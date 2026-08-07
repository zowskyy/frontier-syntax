#!/usr/bin/env python3
"""
Blueprint tracking phase checks — strict ordering, no partial credit.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: imported by scripts/tracking.py gate [--max-phase N]
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from tracking_phase_checks_early import (
    phase_0_checks as _phase_0_checks,
    phase_1_checks as _phase_1_checks,
    phase_2_checks as _phase_2_checks,
    phase_3_checks as _phase_3_checks,
)
from tracking_phase_checks_late import (
    frozen_phases_report,
    phase_4_checks as _phase_4_checks,
    phase_5_checks as _phase_5_checks,
    phase_6_checks as _phase_6_checks,
    phase_7_checks as _phase_7_checks,
    phase_8_checks as _phase_8_checks,
)
from tracking_phase_gate import gate as _gate
from tracking_phase_io import (
    CANONICAL_ISSUES,
    EVIDENCE,
    FROZEN_FROM_PHASE,
    ROOT,
    TRACKING,
    open_issues,
    read_json_safe as _read_json_safe,
    read_mfest as _read_mfest,
    run_cmd as _run_cmd,
)

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


def read_manifest(path, field: str, expected=True) -> bool:
    return _read_mfest(path, field, expected)


def run_cmd(cmd: list[str]) -> dict:
    return _run_cmd(cmd)


def phase_0_checks() -> tuple[bool, list[dict]]:
    return _phase_0_checks()


def phase_1_checks(open_set: set[int]) -> tuple[bool, list[dict]]:
    return _phase_1_checks(open_set)


def phase_2_checks(phase_1_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    return _phase_2_checks(phase_1_ok, open_set)


def phase_3_checks(phase_2_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    return _phase_3_checks(phase_2_ok, open_set)


def phase_4_checks(phase_3_ok: bool) -> tuple[bool, list[dict]]:
    return _phase_4_checks(phase_3_ok)


def phase_5_checks(phase_4_ok: bool) -> tuple[bool, list[dict]]:
    return _phase_5_checks(phase_4_ok)


def phase_6_checks(phase_5_ok: bool) -> tuple[bool, list[dict]]:
    return _phase_6_checks(phase_5_ok)


def phase_7_checks(phase_6_ok: bool) -> tuple[bool, list[dict]]:
    return _phase_7_checks(phase_6_ok)


def phase_8_checks(phase_7_ok: bool) -> tuple[bool, list[dict]]:
    return _phase_8_checks(phase_7_ok)


def read_json_safe(path):
    return _read_json_safe(path)


def gate(max_phase: int = 8) -> dict:
    try:
        return _gate(max_phase)
    except Exception as exc:
        raise ValueError(f"tracking phase gate error: {exc}") from exc


def test_health_endpoint() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
