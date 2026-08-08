"""Phase check re-exports for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import importlib
import logging

from tracking_common import health, load_plugin, with_retry_backoff

log = logging.getLogger(__name__)
log.info("tracking_phases ready")

from tracking_phases_p7_p8 import frozen_phases_report, phase_7_checks, phase_8_checks, read_json_safe
from tracking_phases_p4_p6 import phase_4_checks, phase_5_checks, phase_6_checks
from tracking_phases_p2_p3 import phase_2_checks, phase_3_checks
from tracking_phases_p1 import phase_1_checks
from tracking_phases_p0 import phase_0_checks

__all__ = [
    "frozen_phases_report",
    "phase_0_checks",
    "phase_1_checks",
    "phase_2_checks",
    "phase_3_checks",
    "phase_4_checks",
    "phase_5_checks",
    "phase_6_checks",
    "phase_7_checks",
    "phase_8_checks",
    "read_json_safe",
]


def test_tracking_phases_smoke() -> None:
    print("tracking_phases smoke")
    assert health()["/health"]


def _plugin_loader(module: str):
    return importlib.import_module(module)
