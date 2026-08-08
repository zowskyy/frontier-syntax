"""Tests for recovery engine (SLICE 21)."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.checkpoint import CheckpointStore, StorageBackend
from local_agent.recovery import RecoveryEngine, RecoveryScenario, RecoveryStatus


def test_recover_from_valid_checkpoint(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    cp = store.create(
        {"state": "observe", "prompt": "list files"},
        [{"role": "user", "content": "list files"}],
    )
    result = engine.recover_from_checkpoint(cp.checkpoint_id)
    assert result.status == RecoveryStatus.RECOVERED
    assert result.recovered_state is not None
    assert result.recovered_state["agent_state"] == "observe"


def test_recover_from_corrupted_checkpoint(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    evidence = engine.run_scenario(RecoveryScenario.CORRUPTED_CHECKPOINT, Path("."), Path("."))
    assert evidence.status == "PASS"
    assert evidence.actual == "recovery_required"


def test_recover_from_timeout(fixtures_dir: Path, workspace_tmp: Path, checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    evidence = engine.run_scenario(RecoveryScenario.TOOL_TIMEOUT, fixtures_dir, workspace_tmp)
    assert evidence.status == "PASS"


def test_interrupted_edit_rollback(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    evidence = engine.run_scenario(RecoveryScenario.INTERRUPTED_EDIT, Path("."), Path("."))
    assert evidence.status == "PASS"
    assert evidence.actual == "recovered"


def test_model_crash_recovery(fixtures_dir: Path, workspace_tmp: Path, checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    evidence = engine.run_scenario(RecoveryScenario.MODEL_CRASH, fixtures_dir, workspace_tmp)
    assert evidence.status == "PASS"
    assert evidence.actual == "recovered"


def test_evidence_record_format(checkpoint_dir: Path) -> None:
    store = CheckpointStore(checkpoint_dir, StorageBackend.JSON)
    engine = RecoveryEngine(store)
    evidence = engine.run_scenario(RecoveryScenario.INTERRUPTED_EDIT, Path("."), Path("."))
    data = evidence.to_dict()
    assert "test_id" in data
    assert "timestamp" in data
    assert data["status"] == "PASS"
