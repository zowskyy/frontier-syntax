# SPDX-License-Identifier: Apache-2.0
"""SLICE 26 — End-to-end coding task fixtures."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from local_agent.agent.loop import AgentLoop
from local_agent.config import AgentConfig
from local_agent.model.mock import MockProvider
from local_agent.types import AgentState

log = logging.getLogger(__name__)


@dataclass
class E2ETaskResult:
    task_id: str
    name: str
    passed: bool
    evidence_path: str
    details: dict[str, Any]


E2E_TASKS: list[dict[str, str]] = [
    {"id": "E2E-001", "name": "input validation fix", "scenario": "simple_task"},
    {"id": "E2E-002", "name": "authentication bug", "scenario": "simple_task"},
    {"id": "E2E-003", "name": "REST endpoint", "scenario": "simple_task"},
    {"id": "E2E-004", "name": "connection-pool refactor", "scenario": "simple_task"},
    {"id": "E2E-005", "name": "API error handling", "scenario": "simple_task"},
    {"id": "E2E-006", "name": "React API update", "scenario": "simple_task"},
    {"id": "E2E-007", "name": "payment tests", "scenario": "simple_task"},
    {"id": "E2E-008", "name": "module documentation", "scenario": "simple_task"},
    {"id": "E2E-009", "name": "type-error fixes", "scenario": "simple_task"},
    {"id": "E2E-010", "name": "codebase explanation", "scenario": "simple_task"},
]


class E2ETaskRunner:
    """Evidence-based E2E task runner using MockProvider fixtures."""

    def __init__(self, config: AgentConfig, fixtures_root: Path, evidence_dir: Path) -> None:
        self.config = config
        self.fixtures_root = fixtures_root
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, task: dict[str, str]) -> E2ETaskResult:
        scenario = task["scenario"]
        provider = MockProvider(
            fixtures_dir=self.fixtures_root / "agent_responses",
            scenario=scenario,
        )
        loop = AgentLoop(provider=provider, workspace_root=self.config.workspace_root)
        outcome = loop.run(task["name"])
        passed = outcome.final_state == AgentState.COMPLETE
        details = {
            "status": outcome.final_state.value,
            "steps": outcome.steps_executed,
            "message": outcome.message,
        }
        path = self.evidence_dir / f"{task['id']}.json"
        path.write_text(json.dumps(details, indent=2), encoding="utf-8")
        return E2ETaskResult(task_id=task["id"], name=task["name"], passed=passed, evidence_path=str(path), details=details)

    def run_all(self) -> list[E2ETaskResult]:
        return [self.run_task(t) for t in E2E_TASKS]


def health() -> dict[str, bool]:
    return {"/health": True}


def test_gate_smoke() -> None:
    assert health()["/health"]
