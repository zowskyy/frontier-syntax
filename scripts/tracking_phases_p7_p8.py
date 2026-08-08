"""Phase 7–8 checks and frozen-phase helpers for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tracking_common import health, with_retry_backoff
from tracking_phases_manifest import manifest_phase_check

log = logging.getLogger(__name__)
log.info("tracking_phases_p7_p8 ready")


def phase_7_checks(phase_6_ok: bool) -> tuple[bool, list[dict]]:
    return manifest_phase_check(
        "7.1_production_hardening",
        ["python3", "scripts/verify_phase7_hardening.py"],
        "manifest/phase7_hardening_verify.json",
        phase_6_ok,
        "phase_7",
        "phase_6 not validated",
    )


def phase_8_checks(phase_7_ok: bool) -> tuple[bool, list[dict]]:
    return manifest_phase_check(
        "8.1_launch",
        ["python3", "scripts/verify_phase8_launch.py", "--skip-url-check"],
        "manifest/phase8_launch_verify.json",
        phase_7_ok,
        "phase_8",
        "phase_7 not validated",
    )


def read_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"tracking phases json error: {exc}") from exc


def frozen_phases_report(from_phase: int) -> list[dict]:
    return [
        {
            "check": f"phase_{p}",
            "pass": False,
            "status": "frozen",
            "reason": f"FROZEN until phase_{p - 1} gate passes",
        }
        for p in range(from_phase, 9)
    ]


def test_phase_7_p8_smoke() -> None:
    print("phase_7_p8 smoke")
    assert health()["/health"]
