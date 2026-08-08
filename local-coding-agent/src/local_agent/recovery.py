"""Recovery engine for failure scenarios."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from local_agent.agent.loop import AgentLoop, AgentLoopError, AgentTimeoutError
from local_agent.checkpoint import (
    CheckpointCorruptedError,
    CheckpointPayload,
    CheckpointStore,
)
from local_agent.model.mock import MockProvider
from local_agent.types import AgentState


class RecoveryScenario(str, Enum):
    MODEL_CRASH = "model_crash"
    TOOL_TIMEOUT = "tool_timeout"
    CORRUPTED_CHECKPOINT = "corrupted_checkpoint"
    INTERRUPTED_EDIT = "interrupted_edit"


class RecoveryStatus(str, Enum):
    RECOVERED = "recovered"
    RECOVERY_REQUIRED = "recovery_required"
    FAILED = "failed"


@dataclass
class RecoveryEvidence:
    test_id: str
    scenario: RecoveryScenario
    timestamp: str
    expected: str
    actual: str
    status: str
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "scenario": self.scenario.value,
            "timestamp": self.timestamp,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
            "artifacts": self.artifacts,
        }


@dataclass
class RecoveryResult:
    status: RecoveryStatus
    message: str
    checkpoint_id: str | None = None
    recovered_state: dict[str, Any] | None = None
    evidence: RecoveryEvidence | None = None


class RecoveryEngine:
    """Handles deterministic recovery from failures."""

    def __init__(self, checkpoint_store: CheckpointStore) -> None:
        self.checkpoint_store = checkpoint_store
        self._pending_edits: dict[str, dict[str, Any]] = {}

    def save_checkpoint_from_loop(self, loop: AgentLoop, task_state: dict[str, Any]) -> CheckpointPayload:
        return self.checkpoint_store.create(
            task_state=task_state,
            conversation_state=task_state.get("conversation", []),
        )

    def recover_from_checkpoint(self, checkpoint_id: str) -> RecoveryResult:
        try:
            payload = self.checkpoint_store.restore(checkpoint_id)
            return RecoveryResult(
                status=RecoveryStatus.RECOVERED,
                message="Restored from valid checkpoint",
                checkpoint_id=checkpoint_id,
                recovered_state={
                    "task_state": payload.task_state,
                    "conversation_state": payload.conversation_state,
                    "agent_state": payload.task_state.get("state", AgentState.PLAN.value),
                },
            )
        except CheckpointCorruptedError as exc:
            return RecoveryResult(
                status=RecoveryStatus.RECOVERY_REQUIRED,
                message=f"Corrupted checkpoint: {exc}",
                checkpoint_id=checkpoint_id,
            )

    def recover_from_timeout(
        self,
        loop: AgentLoop,
        prompt: str,
        last_checkpoint_id: str | None = None,
    ) -> RecoveryResult:
        if last_checkpoint_id:
            result = self.recover_from_checkpoint(last_checkpoint_id)
            if result.status == RecoveryStatus.RECOVERED:
                return result
        return RecoveryResult(
            status=RecoveryStatus.RECOVERY_REQUIRED,
            message="Agent timed out; manual recovery required",
            checkpoint_id=last_checkpoint_id,
        )

    def begin_edit(self, edit_id: str, file_path: str, original_hash: str, content: str) -> None:
        self._pending_edits[edit_id] = {
            "file_path": file_path,
            "original_hash": original_hash,
            "content": content,
            "committed": False,
        }

    def rollback_edit(self, edit_id: str) -> RecoveryResult:
        edit = self._pending_edits.pop(edit_id, None)
        if not edit:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                message=f"No pending edit: {edit_id}",
            )
        return RecoveryResult(
            status=RecoveryStatus.RECOVERED,
            message="Interrupted edit rolled back",
            recovered_state={"edit_id": edit_id, "rolled_back": True},
        )

    def run_scenario(
        self,
        scenario: RecoveryScenario,
        fixtures_dir: Path,
        workspace: Path,
        checkpoint_id: str | None = None,
    ) -> RecoveryEvidence:
        test_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        if scenario == RecoveryScenario.CORRUPTED_CHECKPOINT:
            return self._scenario_corrupted_checkpoint(test_id, timestamp, checkpoint_id)

        if scenario == RecoveryScenario.TOOL_TIMEOUT:
            return self._scenario_tool_timeout(test_id, timestamp, fixtures_dir, workspace)

        if scenario == RecoveryScenario.INTERRUPTED_EDIT:
            return self._scenario_interrupted_edit(test_id, timestamp)

        return self._scenario_model_crash(test_id, timestamp, fixtures_dir, workspace)

    def _scenario_corrupted_checkpoint(
        self, test_id: str, timestamp: str, checkpoint_id: str | None
    ) -> RecoveryEvidence:
        if not checkpoint_id:
            cp = self.checkpoint_store.create({"state": "observe"}, [])
            checkpoint_id = cp.checkpoint_id

        path = self.checkpoint_store.store_path / f"{checkpoint_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["state_hash"] = "corrupted"
            path.write_text(json.dumps(data), encoding="utf-8")

        result = self.recover_from_checkpoint(checkpoint_id)
        return RecoveryEvidence(
            test_id=test_id,
            scenario=RecoveryScenario.CORRUPTED_CHECKPOINT,
            timestamp=timestamp,
            expected="RECOVERY_REQUIRED",
            actual=result.status.value,
            status="PASS" if result.status == RecoveryStatus.RECOVERY_REQUIRED else "FAIL",
            artifacts={"checkpoint_id": checkpoint_id},
        )

    def _scenario_tool_timeout(
        self, test_id: str, timestamp: str, fixtures_dir: Path, workspace: Path
    ) -> RecoveryEvidence:
        loop = AgentLoop(
            provider=MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task", generate_delay=0.05),
            workspace_root=workspace,
            timeout_seconds=0.001,
        )
        try:
            loop.run("list files")
            actual = "completed"
        except AgentTimeoutError:
            result = self.recover_from_timeout(loop, "list files")
            actual = result.status.value

        return RecoveryEvidence(
            test_id=test_id,
            scenario=RecoveryScenario.TOOL_TIMEOUT,
            timestamp=timestamp,
            expected="recovery_required",
            actual=actual,
            status="PASS" if actual == "recovery_required" else "FAIL",
        )

    def _scenario_interrupted_edit(self, test_id: str, timestamp: str) -> RecoveryEvidence:
        edit_id = "edit-001"
        self.begin_edit(edit_id, "main.py", "abc123", "partial content")
        result = self.rollback_edit(edit_id)
        return RecoveryEvidence(
            test_id=test_id,
            scenario=RecoveryScenario.INTERRUPTED_EDIT,
            timestamp=timestamp,
            expected="recovered",
            actual=result.status.value,
            status="PASS" if result.status == RecoveryStatus.RECOVERED else "FAIL",
            artifacts=result.recovered_state or {},
        )

    def _scenario_model_crash(
        self, test_id: str, timestamp: str, fixtures_dir: Path, workspace: Path
    ) -> RecoveryEvidence:
        cp = self.checkpoint_store.create(
            {"state": "model", "prompt": "list files"},
            [{"role": "user", "content": "list files"}],
        )
        result = self.recover_from_checkpoint(cp.checkpoint_id)
        return RecoveryEvidence(
            test_id=test_id,
            scenario=RecoveryScenario.MODEL_CRASH,
            timestamp=timestamp,
            expected="recovered",
            actual=result.status.value,
            status="PASS" if result.status == RecoveryStatus.RECOVERED else "FAIL",
            artifacts={"checkpoint_id": cp.checkpoint_id},
        )
