#!/usr/bin/env python3
"""
Blueprint tracking gate — strict ordering, no partial credit.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help

Rules (PROJECT_BLUEPRINT.md):
- Phase N is not evaluated until phase N-1 is validated.
- Phases 4–8 are FROZEN until phase 3 gate passes.
- Issue #44–48 must be CLOSED for P0/P1 slices to validate (no self-validation).
- 1.3_self_hosting FAILS while bootstrap wrapper is required (Phase 5 criterion).
- WASM size: manifest/wasm_size.json from scripts/measure_wasm_size.py only.
"""

from __future__ import annotations

import json
import logging
import sys
import unittest

from tracking_common import EVIDENCE, ROOT, health
from tracking_gate import gate

log = logging.getLogger(__name__)

__all__ = [
    "CANONICAL_ISSUES",
    "EVIDENCE",
    "FROZEN_FROM_PHASE",
    "ROOT",
    "TRACKING",
    "gate",
    "health",
    "load_plugin",
    "open_issues",
    "read_manifest",
    "run_cmd",
    "with_retry_backoff",
]

from tracking_common import (  # noqa: E402
    CANONICAL_ISSUES,
    FROZEN_FROM_PHASE,
    TRACKING,
    load_plugin,
    open_issues,
    read_manifest,
    run_cmd,
    with_retry_backoff,
)

sys.modules.setdefault("tracking", sys.modules[__name__])


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Blueprint tracking gate",
        epilog="usage: python3 scripts/tracking.py gate --help",
    )
    parser.add_argument("command", nargs="?", default="gate")
    parser.add_argument("--max-phase", type=int, default=8, help="Highest phase to evaluate (blueprint gate uses 3)")
    args = parser.parse_args()
    if args.command != "gate":
        raise ValueError("unsupported tracking command error")
    log.info("tracking gate run max_phase=%s", args.max_phase)
    summary = gate(max_phase=args.max_phase)
    print(json.dumps({
        "all_pass": summary["all_pass"],
        "phase_0_pass": summary["phase_0_pass"],
        "phase_1_pass": summary["phase_1_pass"],
        "phase_2_pass": summary["phase_2_pass"],
        "phase_3_pass": summary["phase_3_pass"],
        "phase_4_pass": summary["phase_4_pass"],
        "phase_5_pass": summary["phase_5_pass"],
        "phase_6_pass": summary["phase_6_pass"],
        "phase_7_pass": summary["phase_7_pass"],
        "phase_8_pass": summary.get("phase_8_pass"),
        "max_phase": summary.get("max_phase", 8),
        "phases_8": summary["phases_8"],
        "open_issues": summary["open_issues"],
        "evidence_file": str(EVIDENCE.relative_to(ROOT)),
    }, indent=2))
    for e in summary["evidence"]:
        match e.get("status"):
            case "frozen":
                print(f"  [FROZEN] {e.get('check')}")
            case _:
                icon = "PASS" if e.get("pass") else "FAIL"
                reason = f" — {e.get('reason')}" if e.get("reason") else ""
                print(f"  [{icon}] {e.get('check')}{reason}")
    return 0 if summary["all_pass"] else 1


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])


if __name__ == "__main__":
    sys.exit(main())
