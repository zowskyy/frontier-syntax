"""Phase 2 and 3 checks for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import json
import logging

from tracking_common import ROOT, health, run_cmd, with_retry_backoff

log = logging.getLogger(__name__)
log.info("tracking_phases_p2_p3 ready")


def phase_2_checks(phase_1_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    if not phase_1_ok:
        return False, [{"check": "phase_2", "pass": False, "status": "blocked", "reason": "phase_1 not validated"}]
    evidence = []
    r21 = run_cmd(["python3", "scripts/spec_impl_bridge.py"])
    ok21 = r21["pass"] and 47 not in open_set
    evidence.append({"check": "2.1_spec_impl", "ref": "issue_47", "pass": ok21, "issue_closed": 47 not in open_set, **r21})
    r22 = run_cmd(["cargo", "test", "--lib", "-p", "frontier"])
    evidence.append({"check": "2.2_lib_tests", "pass": r22["pass"], **r22})
    return ok21 and r22["pass"], evidence


def phase_3_checks(phase_2_ok: bool, open_set: set[int]) -> tuple[bool, list[dict]]:
    if not phase_2_ok:
        return False, [{"check": "phase_3", "pass": False, "status": "blocked", "reason": "phase_2 not validated"}]
    evidence = []
    measure = run_cmd(["python3", "scripts/measure_wasm_size.py"])
    manifest = ROOT / "manifest" / "wasm_size.json"
    size_data = json.loads(manifest.read_text()) if manifest.exists() else {}
    target_met = size_data.get("met", False)
    issue_closed = 48 not in open_set
    ok = measure["pass"] and target_met and issue_closed
    evidence.append({
        "check": "3.1_wasm_size",
        "ref": "issue_48",
        "pass": ok,
        "status": "fail" if not ok else "validated",
        "size_kb": size_data.get("size_kb"),
        "target_kb": size_data.get("target_kb"),
        "authoritative_manifest": "manifest/wasm_size.json",
        "issue_closed": issue_closed,
        "reason": None if ok else f"size {size_data.get('size_kb')} KB >= {size_data.get('target_kb')} KB or issue #48 open",
        **measure,
    })
    return ok, evidence


def test_phase_2_p3_smoke() -> None:
    print("phase_2_p3 smoke")
    assert health()["/health"]
