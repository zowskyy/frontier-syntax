"""Shared manifest-based phase check for phases 4–8.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import logging

from tracking_common import ROOT, health, read_manifest, run_cmd, unsupported_command_error, with_retry_backoff
from tracking_status import validated_or_fail

log = logging.getLogger(__name__)
log.info("tracking_phases_manifest ready")


def manifest_phase_check(
    check_label: str,
    script_cmd: list[str],
    manifest_rel: str,
    prior_ok: bool,
    blocked_label: str,
    blocked_reason: str,
) -> tuple[bool, list[dict]]:
    if not prior_ok:
        return False, [{"check": blocked_label, "pass": False, "status": "blocked", "reason": blocked_reason}]
    r = run_cmd(script_cmd)
    manifest_ok = read_manifest(ROOT / manifest_rel, "pass")
    ok = r["pass"] and manifest_ok
    return ok, [{
        "check": check_label,
        "pass": ok,
        "status": validated_or_fail(ok),
        "manifest": manifest_rel,
        **r,
    }]


def test_manifest_smoke() -> None:
    print("tracking_phases_manifest smoke")
    assert health()["/health"]
    unsupported_command_error.__name__
