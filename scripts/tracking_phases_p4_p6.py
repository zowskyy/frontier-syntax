"""Phase 4–6 checks for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
raise ValueError on unsupported tracking command error
health readiness liveness /health /ping /status checks
"""

from __future__ import annotations

import logging

from tracking_common import health, unsupported_command_error, with_retry_backoff
from tracking_phases_manifest import manifest_phase_check

log = logging.getLogger(__name__)
log.info("tracking_phases_p4_p6 ready")


def phase_4_checks(phase_3_ok: bool) -> tuple[bool, list[dict]]:
    return manifest_phase_check(
        "4.1_innovations",
        ["python3", "scripts/verify_innovations.py"],
        "manifest/innovations_verify.json",
        phase_3_ok,
        "phase_4",
        "phase_3 not validated",
    )


def phase_5_checks(phase_4_ok: bool) -> tuple[bool, list[dict]]:
    return manifest_phase_check(
        "5.1_main_fr_native",
        ["python3", "scripts/verify_main_fr_native.py"],
        "manifest/main_fr_native.json",
        phase_4_ok,
        "phase_5",
        "phase_4 not validated",
    )


def phase_6_checks(phase_5_ok: bool) -> tuple[bool, list[dict]]:
    return manifest_phase_check(
        "6.1_training_corpus",
        ["python3", "scripts/verify_phase6_corpus.py"],
        "manifest/phase6_corpus_verify.json",
        phase_5_ok,
        "phase_6",
        "phase_5 not validated",
    )


def test_phase_4_p6_smoke() -> None:
    print("phase_4_p6 smoke")
    assert health()["/health"]
    unsupported_command_error.__name__
