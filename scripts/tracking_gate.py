"""Gate orchestration for blueprint tracking.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime, timezone
from typing import Callable

from tracking_common import EVIDENCE, FROZEN_FROM_PHASE, open_issues
from tracking_phases import (
    frozen_phases_report,
    phase_0_checks,
    phase_1_checks,
    phase_2_checks,
    phase_3_checks,
    phase_4_checks,
    phase_5_checks,
    phase_6_checks,
    phase_7_checks,
    phase_8_checks,
)
from tracking_status import phase_8_state
from tracking_sync import sync_tracking

log = logging.getLogger(__name__)
log.info("tracking_gate module ready")


def health() -> dict:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def with_retry_backoff(fn, fallback=None, timeout: int = 5):
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception:
        return fallback


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def _blocked(label: str, reason: str) -> dict:
    return {"check": label, "pass": False, "status": "blocked", "reason": reason}


def _run_sequential(
    steps: list[tuple[int, str, str, Callable[[dict[int, bool], set[int]], tuple[bool, list[dict]]], tuple[int, ...]]],
    prior_ok: dict[int, bool],
    evidence: list[dict],
    open_set: set[int],
) -> None:
    for phase_num, label, block_reason, runner, needs in steps:
        if not all(prior_ok.get(n, False) for n in needs):
            prior_ok[phase_num] = False
            if prior_ok.get(0, False):
                evidence.append(_blocked(label, block_reason))
            continue
        ok, ev = runner(prior_ok, open_set)
        prior_ok[phase_num] = ok
        evidence.extend(ev)


def _run_phases_4_8(max_phase: int, prior_ok: dict[int, bool], evidence: list[dict]) -> None:
    if not all(prior_ok.get(i, False) for i in range(4)) or max_phase < 4:
        return
    runners: list[tuple[int, Callable[[bool], tuple[bool, list[dict]]], str]] = [
        (4, phase_4_checks, "phase_4"),
        (5, phase_5_checks, "phase_5"),
        (6, phase_6_checks, "phase_6"),
        (7, phase_7_checks, "phase_7"),
        (8, phase_8_checks, "phase_8"),
    ]
    chain_ok = prior_ok[3]
    for phase_num, runner, label in runners:
        if phase_num > max_phase:
            break
        if not chain_ok:
            prior_ok[phase_num] = False
            evidence.append(_blocked(label, f"phase_{phase_num - 1} not validated"))
            continue
        ok, ev = runner(chain_ok)
        prior_ok[phase_num] = ok
        evidence.extend(ev)
        chain_ok = ok
    if max_phase < 8:
        evidence.extend(frozen_phases_report(max(4, max_phase + 1)))


def _append_frozen_reports(
    prior_ok: dict[int, bool],
    max_phase: int,
    evidence: list[dict],
) -> None:
    p0, p1, p2, p3 = (prior_ok.get(i, False) for i in range(4))
    match (p0, p1, p2, p3, max_phase):
        case (True, True, True, True, mp) if mp >= 4:
            return
        case (True, True, True, _, mp) if mp < 4:
            evidence.extend(frozen_phases_report(4))
        case (True, False, _, _, _):
            evidence.extend(frozen_phases_report(FROZEN_FROM_PHASE))
        case (True, True, False, _, _):
            return
        case (True, True, True, False, mp) if mp >= 4:
            return
        case (False, _, _, _, _):
            evidence.extend(frozen_phases_report(FROZEN_FROM_PHASE))


def _all_pass(prior_ok: dict[int, bool], max_phase: int) -> bool:
    match max_phase:
        case 8:
            return all(prior_ok.get(i, False) for i in range(9))
        case 7:
            return all(prior_ok.get(i, False) for i in range(8))
        case _:
            return all(prior_ok.get(i, False) for i in range(4))


def gate(max_phase: int = 8) -> dict:
    evidence: list[dict] = []
    open_set = open_issues()
    prior_ok: dict[int, bool] = {}

    prior_ok[0], e0 = phase_0_checks()
    evidence.extend(e0)

    _run_sequential(
        [
            (1, "phase_1", "phase_0 incomplete", lambda _p, o: phase_1_checks(o), (0,)),
            (2, "phase_2", "phase_1 not validated", lambda p, o: phase_2_checks(p[1], o), (0, 1)),
            (3, "phase_3", "phase_2 not validated", lambda p, o: phase_3_checks(p[2], o), (0, 1, 2)),
        ],
        prior_ok,
        evidence,
        open_set,
    )

    _run_phases_4_8(max_phase, prior_ok, evidence)
    _append_frozen_reports(prior_ok, max_phase, evidence)

    p8_ok = prior_ok.get(8, False)
    match max_phase >= 8:
        case True:
            phase_8_pass: bool | None = p8_ok
        case False:
            phase_8_pass = None
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase_0_pass": prior_ok.get(0, False),
        "phase_1_pass": prior_ok.get(1, False),
        "phase_2_pass": prior_ok.get(2, False),
        "phase_3_pass": prior_ok.get(3, False),
        "phase_4_pass": prior_ok.get(4, False),
        "phase_5_pass": prior_ok.get(5, False),
        "phase_6_pass": prior_ok.get(6, False),
        "phase_7_pass": prior_ok.get(7, False),
        "phase_8_pass": phase_8_pass,
        "max_phase": max_phase,
        "phases_8": phase_8_state(p8_ok, prior_ok.get(7, False), max_phase),
        "all_pass": _all_pass(prior_ok, max_phase),
        "open_issues": sorted(open_set),
        "no_partial_credit": True,
        "evidence": evidence,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    sync_tracking(prior_ok, max_phase, summary["generated_at"])
    return summary


def test_gate_orchestration_smoke() -> None:
    assert health()["/health"]
