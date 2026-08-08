"""Safe checkpoint storage without pickle."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


CHECKPOINT_SCHEMA_VERSION = 1


class CheckpointError(Exception):
    """Base checkpoint error."""


class CheckpointCorruptedError(CheckpointError):
    """Raised when checkpoint hash verification fails."""


class CheckpointSchemaError(CheckpointError):
    """Raised when schema version is incompatible."""


class StorageBackend(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"


@dataclass
class CheckpointPayload:
    task_state: dict[str, Any]
    conversation_state: list[dict[str, Any]]
    schema_version: int = CHECKPOINT_SCHEMA_VERSION
    state_hash: str = ""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_hash(self) -> str:
        body = {
            "task_state": self.task_state,
            "conversation_state": self.conversation_state,
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def seal(self) -> CheckpointPayload:
        self.state_hash = self.compute_hash()
        return self

    def verify(self) -> None:
        expected = self.compute_hash()
        if self.state_hash != expected:
            raise CheckpointCorruptedError(
                f"Checkpoint hash mismatch: expected {expected}, got {self.state_hash}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_state": self.task_state,
            "conversation_state": self.conversation_state,
            "schema_version": self.schema_version,
            "state_hash": self.state_hash,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointPayload:
        return cls(
            task_state=data["task_state"],
            conversation_state=data["conversation_state"],
            schema_version=data.get("schema_version", CHECKPOINT_SCHEMA_VERSION),
            state_hash=data.get("state_hash", ""),
            checkpoint_id=data.get("checkpoint_id", str(uuid.uuid4())),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class CheckpointStore:
    """JSON and SQLite checkpoint storage with integrity verification."""

    def __init__(self, store_path: str | Path, backend: StorageBackend = StorageBackend.JSON) -> None:
        self.store_path = Path(store_path)
        self.backend = backend
        self.store_path.mkdir(parents=True, exist_ok=True)
        if backend == StorageBackend.SQLITE:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        db_path = self.store_path / "checkpoints.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    state_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create(
        self,
        task_state: dict[str, Any],
        conversation_state: list[dict[str, Any]],
    ) -> CheckpointPayload:
        payload = CheckpointPayload(
            task_state=task_state,
            conversation_state=conversation_state,
        ).seal()
        self._save(payload)
        return payload

    def restore(self, checkpoint_id: str) -> CheckpointPayload:
        payload = self._load(checkpoint_id)
        if payload.schema_version > CHECKPOINT_SCHEMA_VERSION:
            raise CheckpointSchemaError(
                f"Unsupported schema version {payload.schema_version} "
                f"(max supported: {CHECKPOINT_SCHEMA_VERSION})"
            )
        payload.verify()
        return payload

    def list_checkpoints(self) -> list[str]:
        if self.backend == StorageBackend.JSON:
            return sorted(p.stem for p in self.store_path.glob("*.json"))
        db_path = self.store_path / "checkpoints.db"
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT checkpoint_id FROM checkpoints ORDER BY created_at").fetchall()
        return [row[0] for row in rows]

    def _save(self, payload: CheckpointPayload) -> None:
        if self.backend == StorageBackend.JSON:
            path = self.store_path / f"{payload.checkpoint_id}.json"
            path.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
            return
        db_path = self.store_path / "checkpoints.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                (checkpoint_id, schema_version, state_hash, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.checkpoint_id,
                    payload.schema_version,
                    payload.state_hash,
                    json.dumps(payload.to_dict()),
                    payload.created_at,
                ),
            )

    def _load(self, checkpoint_id: str) -> CheckpointPayload:
        if self.backend == StorageBackend.JSON:
            path = self.store_path / f"{checkpoint_id}.json"
            if not path.exists():
                raise CheckpointError(f"Checkpoint not found: {checkpoint_id}")
            data = json.loads(path.read_text(encoding="utf-8"))
            return CheckpointPayload.from_dict(data)

        db_path = self.store_path / "checkpoints.db"
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT payload FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
        if not row:
            raise CheckpointError(f"Checkpoint not found: {checkpoint_id}")
        return CheckpointPayload.from_dict(json.loads(row[0]))
