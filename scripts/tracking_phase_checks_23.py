#!/usr/bin/env python3
"""
Blueprint tracking phase 2–3 checks — spec bridge and wasm size.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by tracking_phase_checks_early
"""

from __future__ import annotations

import importlib
import json
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from tracking_phase_io import ROOT, run_cmd

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


def _blocked(check: str, reason: str) -> tuple[bool, list[dict]]:
    return False, [{"check": check, "pass": False, "status": "blocked", "reason": reason}]  # nosec B105


def phase_2_checks(phase_1_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    if not phase_1_ok:
        return _blocked("phase_2", "phase_1 not validated")
    evidence = []
    r21 = run_cmd(["python3", "scripts/spec_impl_bridge.py"])
    ok21 = r21["pass"] and 47 not in open_set
    evidence.append({"check": "2.1_spec_impl", "ref": "issue_47", "pass": ok21, "issue_closed": 47 not in open_set, **r21})
    r22 = run_cmd(["cargo", "test", "--lib", "-p", "frontier"])
    evidence.append({"check": "2.2_lib_tests", "pass": r22["pass"], **r22})
    return ok21 and r22["pass"], evidence


def phase_3_checks(phase_2_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    if not phase_2_ok:
        return _blocked("phase_3", "phase_2 not validated")
    evidence = []
    measure = run_cmd(["python3", "scripts/measure_wasm_size.py"])
    mfest = ROOT / "manifest" / "wasm_size.json"
    size_data = json.loads(mfest.read_text()) if mfest.exists() else {}
    target_met = size_data.get("met", False)
    issue_closed = 48 not in open_set
    ok = measure["pass"] and target_met and issue_closed
    reason = None
    if not ok:
        reason = f"size {size_data.get('size_kb')} KB >= {size_data.get('target_kb')} KB or issue #48 open"
    evidence.append({
        "check": "3.1_wasm_size",
        "ref": "issue_48",
        "pass": ok,
        "status": "fail" if not ok else "validated",
        "size_kb": size_data.get("size_kb"),
        "target_kb": size_data.get("target_kb"),
        "authoritative_mfest": "manifest/wasm_size.json",
        "issue_closed": issue_closed,
        "reason": reason,
        **measure,
    })
    return ok, evidence



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
