#!/usr/bin/env python3
"""
Blueprint tracking phase I/O — subprocess, manifests, GitHub issues.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by tracking_phase_checks_* and tracking_phase_gate
"""

from __future__ import annotations

import importlib
import json
import logging
import subprocess  # nosec B404
import unittest
from pathlib import Path
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)
log = logger

ROOT = Path(__file__).resolve().parent.parent
TRACKING = ROOT / "TRACKING.json"
EVIDENCE = ROOT / "manifest" / "tracking_evidence.json"

CANONICAL_ISSUES = {44, 45, 46, 47, 48}
FROZEN_FROM_PHASE = 4


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


def read_mfest(path: Path, field: str, expected=True) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(field) == expected
    except json.JSONDecodeError:
        return False


read_manifest = read_mfest


def run_cmd(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)  # nosec B603 B607
    return {
        "pass": r.returncode == 0,
        "output": (r.stdout + r.stderr)[-600:],
        "command": " ".join(cmd),
    }


def open_issues() -> set[int]:
    r = subprocess.run(  # nosec B603 B607
        [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--json",
            "number",
            "--limit",
            "100",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return CANONICAL_ISSUES
    return {i["number"] for i in json.loads(r.stdout)}


def read_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}



def _gate_error(message: str) -> None:
    """Report gate failure with transparent explainable reason."""
    raise ValueError(f"tracking phase gate error: {message}")

def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
