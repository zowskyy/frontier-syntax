"""SLICE 11 — FTS5 lexical search with parameterized queries."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from local_agent.knowledge.store import KnowledgeStore


_FTS_SCHEMA_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    text,
    tokenize = 'unicode61'
);
"""


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    text: str
    score: float
    rank: int


class FTSSearch:
    """FTS5-backed lexical search over chunk text."""

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self._ensure_fts()

    def _ensure_fts(self) -> None:
        self.store.connection.executescript(_FTS_SCHEMA_SQL)
        self.store.connection.commit()

    def rebuild_index(self) -> int:
        conn = self.store.connection
        conn.execute("DELETE FROM chunks_fts")
        rows = conn.execute("SELECT id, text FROM chunks ORDER BY document_id, ordinal").fetchall()
        for row in rows:
            conn.execute(
                "INSERT INTO chunks_fts(chunk_id, text) VALUES (?, ?)",
                (row["id"], row["text"]),
            )
        conn.commit()
        return len(rows)

    def index_chunk(self, chunk_id: str, text: str) -> None:
        self.store.connection.execute(
            "INSERT INTO chunks_fts(chunk_id, text) VALUES (?, ?)",
            (chunk_id, text),
        )
        self.store.connection.commit()

    def remove_chunk(self, chunk_id: str) -> None:
        self.store.connection.execute(
            "DELETE FROM chunks_fts WHERE chunk_id = ?",
            (chunk_id,),
        )
        self.store.connection.commit()

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        case_insensitive: bool = True,
        phrase: bool = False,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        fts_query = self._build_fts_query(query, case_insensitive=case_insensitive, phrase=phrase)
        sql = """
            SELECT chunk_id, text, bm25(chunks_fts) AS score
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """
        rows = self.store.connection.execute(sql, (fts_query, limit)).fetchall()
        results: list[SearchResult] = []
        for rank, row in enumerate(rows, start=1):
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    text=row["text"],
                    score=float(row["score"]),
                    rank=rank,
                )
            )
        return results

    @staticmethod
    def _build_fts_query(query: str, *, case_insensitive: bool, phrase: bool) -> str:
        cleaned = query.strip()
        if phrase:
            escaped = cleaned.replace('"', '""')
            return f'"{escaped}"'

        tokens = re.findall(r"[\w$#@]+", cleaned, flags=re.UNICODE)
        if not tokens:
            return cleaned

        parts: list[str] = []
        for token in tokens:
            escaped = token.replace('"', '""')
            if case_insensitive:
                parts.append(f"{escaped}*")
            else:
                parts.append(f'"{escaped}"')
        return " AND ".join(parts)

    def recover_from_corruption(self) -> int:
        conn = self.store.connection
        try:
            conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()
            return 0
        except sqlite3.DatabaseError:
            conn.executescript("DROP TABLE IF EXISTS chunks_fts;")
            self._ensure_fts()
            return self.rebuild_index()
