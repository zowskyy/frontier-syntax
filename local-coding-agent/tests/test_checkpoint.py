"""Tests for checkpoint system (SLICE 20)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_agent.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointCorruptedError,
    CheckpointPayload,
    CheckpointSchemaError,
    CheckpointStore,
    StorageBackend,
)


def test_checkpoint_create_and_restore_json(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    payload = store.create(
        task_state={"state": "observe", "prompt": "test"},
        conversation_state=[{"role": "user", "content": "test"}],
    )
    assert payload.state_hash
    restored = store.restore(payload.checkpoint_id)
    assert restored.task_state["state"] == "observe"
    assert restored.schema_version == CHECKPOINT_SCHEMA_VERSION


def test_checkpoint_hash_verification(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    payload = store.create({"state": "plan"}, [])
    restored = store.restore(payload.checkpoint_id)
    restored.verify()


def test_corrupted_checkpoint_detected(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    payload = store.create({"state": "plan"}, [])
    path = checkpoint_dir / f"{payload.checkpoint_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["state_hash"] = "tampered"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CheckpointCorruptedError):
        store.restore(payload.checkpoint_id)


def test_checkpoint_sqlite_backend(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.SQLITE)
    payload = store.create({"state": "model"}, [{"role": "user", "content": "hi"}])
    restored = store.restore(payload.checkpoint_id)
    assert restored.task_state["state"] == "model"
    assert payload.checkpoint_id in store.list_checkpoints()


def test_schema_version_mismatch(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    payload = CheckpointPayload(
        task_state={"state": "plan"},
        conversation_state=[],
        schema_version=999,
    ).seal()
    store._save(payload)
    with pytest.raises(CheckpointSchemaError):
        store.restore(payload.checkpoint_id)


def test_no_pickle_in_codebase() -> None:
    import local_agent.checkpoint as cp

    source = Path(cp.__file__).read_text(encoding="utf-8")
    assert "import pickle" not in source
    assert "pickle.load" not in source
    assert "pickle.loads" not in source


def test_payload_seal_and_verify() -> None:
    payload = CheckpointPayload(
        task_state={"a": 1},
        conversation_state=[{"role": "user", "content": "x"}],
    ).seal()
    payload.verify()
    assert len(payload.state_hash) == 64
