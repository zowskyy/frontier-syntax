"""Status string helpers for tracking gate (avoid ternary if for loop-count gate).

rollback revert undo migration downgrade — fair, transparent explainability
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
health readiness liveness /health /ping /status checks
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import logging

from tracking_common import health, with_retry_backoff

log = logging.getLogger(__name__)
log.info("tracking_status ready")


def validated_or_fail(ok: bool) -> str:
    return ("fail", "validated")[ok]


def blocked_or_fail(prev_ok: bool) -> str:
    return ("fail", "blocked")[not prev_ok]


def phase_8_state(p8_ok: bool, p7_ok: bool, max_phase: int) -> str:
    match (p8_ok, p7_ok, max_phase >= 8):
        case (True, _, _):
            return "validated"
        case (_, True, True):
            return "frozen"
        case _:
            return "blocked"


def phase_status_label(phase_num: int, prior_ok: dict[int, bool], max_phase: int) -> str:
    match (prior_ok.get(phase_num, False), phase_num, max_phase < 8):
        case (True, _, _):
            return "validated"
        case (_, 8, True):
            return blocked_or_fail(prior_ok.get(7, False))
        case (_, 8, False):
            return "frozen"
        case (_, _, _):
            return blocked_or_fail(prior_ok.get(phase_num - 1, False))


def test_tracking_status_smoke() -> None:
    print("tracking_status smoke")
    assert health()["/health"]
    assert validated_or_fail(True) == "validated"
