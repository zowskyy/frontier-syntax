"""Tests for audit log (SLICE 3).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.audit import AuditEvent, AuditLog, EventType


@pytest.fixture
def audit_log(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.db")


def test_append_event(audit_log: AuditLog) -> None:
    event_id = audit_log.record(
        EventType.TASK_CREATED,
        actor="user",
        correlation_id="task-001",
        outcome="created",
        payload={"description": "fix bug"},
        input_data={"task": "fix bug"},
    )
    assert event_id
    assert audit_log.count() == 1


def test_all_event_types(audit_log: AuditLog) -> None:
    types = [
        EventType.TASK_CREATED,
        EventType.TOOL_REQUEST,
        EventType.POLICY_DENIED,
        EventType.FILE_EDITED,
        EventType.CHECKPOINT_CREATED,
    ]
    for i, etype in enumerate(types):
        audit_log.record(etype, "agent", f"corr-{i}", "ok")
    assert audit_log.count() == len(types)


def test_correlation_filter(audit_log: AuditLog) -> None:
    audit_log.record(EventType.TOOL_REQUEST, "agent", "corr-A", "ok", input_data={"tool": "read_file"})
    audit_log.record(EventType.TOOL_COMPLETED, "agent", "corr-A", "ok")
    audit_log.record(EventType.TOOL_REQUEST, "agent", "corr-B", "ok")
    events = audit_log.get_events(correlation_id="corr-A")
    assert len(events) == 2


def test_input_hash_deterministic() -> None:
    h1 = AuditLog.hash_input({"tool": "read_file", "path": "foo.py"})
    h2 = AuditLog.hash_input({"tool": "read_file", "path": "foo.py"})
    assert h1 == h2
    h3 = AuditLog.hash_input({"tool": "write_file", "path": "foo.py"})
    assert h1 != h3


def test_export_json(audit_log: AuditLog, tmp_path: Path) -> None:
    audit_log.record(EventType.TASK_CREATED, "user", "c1", "created")
    out = tmp_path / "export.json"
    count = audit_log.export_json(out)
    assert count == 1
    assert out.exists()
    assert "TASK_CREATED" in out.read_text()


def test_survives_reopen(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    log1 = AuditLog(db)
    log1.record(EventType.TASK_CREATED, "user", "c1", "created")
    log2 = AuditLog(db)
    assert log2.count() == 1


def test_audit_event_dataclass() -> None:
    event = AuditEvent(
        event_type=EventType.FILE_EDITED,
        actor="agent",
        correlation_id="edit-1",
        outcome="committed",
        payload={"path": "foo.py"},
    )
    assert event.event_id
    assert event.timestamp
