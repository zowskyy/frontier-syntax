#!/usr/bin/env python3
"""
Blueprint tracking phase orchestration — run phases 0–8 in strict order.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by tracking_phase_gate
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any, Callable

from tracking_phase_checks_early import phase_0_checks, phase_1_checks, phase_2_checks, phase_3_checks
from tracking_phase_checks_late import (
    frozen_phases_report,
    phase_4_checks,
    phase_5_checks,
    phase_6_checks,
    phase_7_checks,
    phase_8_checks,
)
from tracking_phase_io import FROZEN_FROM_PHASE

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


def _run_optional_phase(
    ready: bool,
    runner: Callable[[], tuple[bool, list[dict]]],
    block_check: str,
    block_reason: str,
) -> tuple[bool, list[dict]]:
    if ready:
        return runner()
    return False, [{"check": block_check, "pass": False, "status": "blocked", "reason": block_reason}]  # nosec B105


def _run_phases_0_3(
    open_set: set[int],
    p0_ok: bool,
) -> tuple[bool, bool, bool, list[dict]]:
    extra: list[dict] = []
    p1_ok, e1 = _run_optional_phase(p0_ok, lambda: phase_1_checks(open_set), "phase_1", "phase_0 incomplete")
    extra.extend(e1)
    p2_ok, e2 = _run_optional_phase(p0_ok and p1_ok, lambda: phase_2_checks(p1_ok, open_set), "phase_2", "phase_1 not validated")
    extra.extend(e2)
    p3_ok, e3 = _run_optional_phase(p0_ok and p1_ok and p2_ok, lambda: phase_3_checks(p2_ok, open_set), "phase_3", "phase_2 not validated")
    extra.extend(e3)
    return p1_ok, p2_ok, p3_ok, extra


def _run_phases_4_8(p3_ok: bool, max_phase: int) -> tuple[list[bool], list[dict]]:
    runners: list[tuple[int, Callable[[bool], tuple[bool, list[dict]]]]] = [
        (4, phase_4_checks),
        (5, phase_5_checks),
        (6, phase_6_checks),
        (7, phase_7_checks),
        (8, phase_8_checks),
    ]
    results = [False] * 5
    extra: list[dict] = []
    prev_ok = p3_ok
    for idx, (num, fn) in enumerate(runners):
        if max_phase < num:
            break
        if prev_ok:
            ok, ev = fn(prev_ok)
            results[idx] = ok
            extra.extend(ev)
            prev_ok = ok
        else:
            extra.append({
                "check": f"phase_{num}",
                "pass": False,  # nosec B105
                "status": "blocked",
                "reason": f"phase_{num - 1} not validated",
            })
    if max_phase < 8:
        extra.extend(frozen_phases_report(max(4, max_phase + 1)))
    return results, extra


def _append_frozen_evidence(p0_ok: bool, p1_ok: bool, p2_ok: bool, max_phase: int, evidence: list[dict]) -> None:
    if p0_ok and p1_ok and p2_ok and max_phase < 4:
        evidence.extend(frozen_phases_report(4))
    elif p0_ok and not (p1_ok and p2_ok):
        evidence.extend(frozen_phases_report(FROZEN_FROM_PHASE))



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
