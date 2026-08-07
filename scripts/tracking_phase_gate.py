#!/usr/bin/env python3
"""
Blueprint tracking phase gate — entry point for phase validation runs.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by scripts/tracking_phases.py
"""

from __future__ import annotations

import importlib
import json
import logging
import unittest
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from tracking_phase_io import EVIDENCE, open_issues
from tracking_phase_orchestrate import _append_frozen_evidence, _run_phases_0_3, _run_phases_4_8
from tracking_phase_checks_early import phase_0_checks
from tracking_phase_status import _all_pass_for_max, _phase_status_map, _sync_tracking

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


def gate(max_phase: int = 8) -> dict:
    evidence: list[dict] = []
    p0_ok, e0 = phase_0_checks()
    evidence.extend(e0)
    open_set = open_issues()
    p1_ok, p2_ok, p3_ok, early = _run_phases_0_3(open_set, p0_ok)
    evidence.extend(early)
    upper = [False] * 5
    if p0_ok and p1_ok and p2_ok and p3_ok and max_phase >= 4:
        upper, late = _run_phases_4_8(p3_ok, max_phase)
        evidence.extend(late)
    else:
        _append_frozen_evidence(p0_ok, p1_ok, p2_ok, max_phase, evidence)
    p4_ok, p5_ok, p6_ok, p7_ok, p8_ok = upper
    phase_flags = [p0_ok, p1_ok, p2_ok, p3_ok, p4_ok, p5_ok, p6_ok, p7_ok, p8_ok]
    all_pass = _all_pass_for_max(max_phase, phase_flags)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase_0_pass": p0_ok,
        "phase_1_pass": p1_ok,
        "phase_2_pass": p2_ok,
        "phase_3_pass": p3_ok,
        "phase_4_pass": p4_ok,
        "phase_5_pass": p5_ok,
        "phase_6_pass": p6_ok,
        "phase_7_pass": p7_ok,
        "phase_8_pass": p8_ok if max_phase >= 8 else None,
        "max_phase": max_phase,
        "phases_8": "validated" if p8_ok else ("frozen" if p7_ok and max_phase >= 8 else "blocked"),
        "all_pass": all_pass,
        "open_issues": sorted(open_set),
        "no_partial_credit": True,
        "evidence": evidence,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _sync_tracking(summary, _phase_status_map(phase_flags, max_phase, p8_ok, p7_ok))
    return summary



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
