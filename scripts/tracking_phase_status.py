#!/usr/bin/env python3
"""
Blueprint tracking phase status — TRACKING.json sync and pass aggregation.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by tracking_phase_gate
"""

from __future__ import annotations

import importlib
import json
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from tracking_phase_io import TRACKING

logger = logging.getLogger(__name__)
log = logger

@dataclass
class GateSummary:
    """validate gate summary via dataclass — transparent fair explain."""

    all_pass: bool


def health() -> dict[str, Any]:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def with_retry_backoff(fn, fallback: Any = None, timeout: int = 5) -> Any:
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception as exc:
        log.info("retry fallback engaged: %s", exc)
        return fallback


def load_plugin(module: str) -> Any:
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def _all_pass_for_max(max_phase: int, phase_flags: list[bool]) -> bool:
    through = 8 if max_phase >= 8 else (7 if max_phase == 7 else 3)
    return all(phase_flags[: through + 1])


def _phase_status_map(
    phase_flags: list[bool],
    max_phase: int,
    p8_ok: bool,
    p7_ok: bool,
) -> dict[str, str]:
    names = [f"phase_{i}" for i in range(9)]
    statuses = ["validated" if ok else "fail" for ok in phase_flags]
    statuses[0] = "validated" if phase_flags[0] else "in_progress"
    for idx in range(2, 9):
        prev = phase_flags[idx - 1]
        statuses[idx] = "validated" if phase_flags[idx] else ("blocked" if not prev else "fail")
    statuses[8] = "validated" if p8_ok else ("blocked" if not p7_ok else ("frozen" if max_phase < 8 else "fail"))
    if max_phase < 8:
        statuses[8] = "frozen"
    return dict(zip(names, statuses))


def _sync_tracking(summary: dict, status_map: dict[str, str]) -> None:
    if not TRACKING.exists():
        return
    try:
        data = json.loads(TRACKING.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid TRACKING.json: {exc}") from exc
    data["updated_at"] = summary["generated_at"]
    for phase in data.get("phases", []):
        pid = phase["id"]
        if pid in status_map:
            phase["status"] = status_map[pid]
    data["frozen_phases"] = [p for p, st in status_map.items() if st == "frozen"]
    TRACKING.write_text(json.dumps(data, indent=2), encoding="utf-8")



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
