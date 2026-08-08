"""SLICE 13 — Optional Chroma adapter with FTS5 fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from local_agent.knowledge.embedding import EmbeddingProvider

try:
    import chromadb  # type: ignore

    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via tests with import mocking
    chromadb = None
    CHROMADB_AVAILABLE = False


@dataclass(frozen=True)
class ChromaMetadata:
    collection_name: str
    embedding_model: str
    dimension: int
    version: str


@dataclass(frozen=True)
class SemanticSearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]


class ChromaAdapter:
    """Optional semantic search layer; SQLite remains authoritative."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        persist_directory: str | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.persist_directory = persist_directory
        self.enabled = enabled and CHROMADB_AVAILABLE
        self._client: Any | None = None
        self._collection: Any | None = None
        self._metadata: ChromaMetadata | None = None

    @property
    def available(self) -> bool:
        return self.enabled and CHROMADB_AVAILABLE

    @property
    def fallback_to_fts(self) -> bool:
        return not self.available

    def collection_metadata(self) -> ChromaMetadata | None:
        return self._metadata

    def _collection_name(self) -> str:
        model = self.embedding_provider.model_id.replace("/", "_").replace(":", "_")
        return f"chunks_{model}_d{self.embedding_provider.dimension}"

    def _collection_version(self) -> str:
        return f"{self.embedding_provider.model_id}:d{self.embedding_provider.dimension}"

    def connect(self) -> bool:
        if not self.available:
            return False
        assert chromadb is not None
        if self._client is None:
            if self.persist_directory:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            else:
                self._client = chromadb.EphemeralClient()
        name = self._collection_name()
        self._collection = self._client.get_or_create_collection(
            name=name,
            metadata={
                "embedding_model": self.embedding_provider.model_id,
                "dimension": self.embedding_provider.dimension,
                "version": self._collection_version(),
            },
        )
        self._metadata = ChromaMetadata(
            collection_name=name,
            embedding_model=self.embedding_provider.model_id,
            dimension=self.embedding_provider.dimension,
            version=self._collection_version(),
        )
        return True

    def rebuild(self, items: list[tuple[str, str, dict[str, Any]]]) -> int:
        if not self.connect():
            return 0
        assert self._collection is not None
        self._collection.delete(where={})
        if not items:
            return 0

        ids = [item[0] for item in items]
        documents = [item[1] for item in items]
        metadatas = [item[2] for item in items]
        embeddings = [self.embedding_provider.embed(text).vector for text in documents]
        self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        return len(items)

    def query(self, query_text: str, *, limit: int = 20) -> list[SemanticSearchResult]:
        if not self.connect():
            return []
        if not self.embedding_provider.health():
            return []
        assert self._collection is not None
        vector = self.embedding_provider.embed(query_text).vector
        response = self._collection.query(query_embeddings=[vector], n_results=limit)
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        distances = response.get("distances", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]

        results: list[SemanticSearchResult] = []
        for index, chunk_id in enumerate(ids):
            distance = distances[index] if index < len(distances) else 0.0
            score = 1.0 / (1.0 + float(distance))
            results.append(
                SemanticSearchResult(
                    chunk_id=chunk_id,
                    text=documents[index] if index < len(documents) else "",
                    score=score,
                    metadata=metadatas[index] if index < len(metadatas) else {},
                )
            )
        return results
