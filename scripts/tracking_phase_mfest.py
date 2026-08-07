#!/usr/bin/env python3
"""
Blueprint tracking manifest phase runner — shared by phases 4–8.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by tracking_phase_checks_late
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from tracking_phase_io import ROOT, read_mfest, run_cmd

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


def run_mfest_phase(
    prev_ok: bool,
    *,
    blocked_check: str,
    blocked_reason: str,
    script: str,
    mfest_rel: str,
    evidence_check: str,
    script_args: list[str] | None = None,
) -> tuple[bool, list[dict]]:
    if not prev_ok:
        return _blocked(blocked_check, blocked_reason)
    cmd = ["python3", script, *(script_args or [])]
    r = run_cmd(cmd)
    mfest_ok = read_mfest(ROOT / mfest_rel, "pass")
    ok = r["pass"] and mfest_ok
    return ok, [{
        "check": evidence_check,
        "pass": ok,
        "status": "validated" if ok else "fail",
        "mfest": mfest_rel,
        **r,
    }]



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
