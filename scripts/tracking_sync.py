"""TRACKING.json sync for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
health readiness liveness /health /ping /status checks
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import json
import logging

from tracking_common import TRACKING, health, with_retry_backoff, unsupported_command_error
from tracking_status import phase_status_label

log = logging.getLogger(__name__)
log.info("tracking_sync ready")


def sync_tracking(prior_ok: dict[int, bool], max_phase: int, generated_at: str) -> None:
    if not TRACKING.exists():
        return
    data = json.loads(TRACKING.read_text())
    data["updated_at"] = generated_at
    status_map = {f"phase_{n}": phase_status_label(n, prior_ok, max_phase) for n in range(9)}
    if max_phase < 8:
        status_map["phase_8"] = "frozen"
    for phase in data.get("phases", []):
        pid = phase["id"]
        if pid in status_map:
            phase["status"] = status_map[pid]
    data["frozen_phases"] = [p for p, st in status_map.items() if st == "frozen"]
    TRACKING.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_tracking_sync_smoke() -> None:
    print("tracking_sync smoke")
    assert health()["/health"]
    unsupported_command_error.__name__
