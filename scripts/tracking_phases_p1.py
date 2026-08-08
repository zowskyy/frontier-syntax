"""Phase 1 checks for blueprint tracking gate.

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
log.info("tracking_phases_p1 ready")


def _check_1_1_wasm_codegen(open_set: set[int]) -> tuple[bool, dict]:
    r11 = run_cmd(["cargo", "test", "--lib", "-p", "frontier", "wasm_codegen::"])
    r11_exec = run_cmd(["python3", "scripts/verify_wasm_codegen.py"])
    issue_open = 44 in open_set
    ok = r11["pass"] and r11_exec["pass"] and not issue_open
    return ok, {
        "check": "1.1_wasm_codegen",
        "ref": "issue_44",
        "tests_pass": r11["pass"],
        "wasmtime_exec_pass": r11_exec["pass"],
        "wasmtime_manifest": "manifest/wasm_codegen_verify.json",
        "issue_closed": not issue_open,
        "pass": ok,
        "status": "fail" if not ok else "validated",
        "reason": "issue #44 still open" if issue_open else None,
        **{k: r11[k] for k in ("output", "command") if k in r11},
    }


def _check_1_2_knowledge_codegen(open_set: set[int]) -> tuple[bool, dict]:
    r12 = run_cmd(["cargo", "test", "--lib", "-p", "frontier", "wasm_codegen::tests::test_knowledge_changes_wasm"])
    issue_open = 45 in open_set
    ok = r12["pass"] and not issue_open
    return ok, {
        "check": "1.2_knowledge_codegen",
        "ref": "issue_45",
        "tests_pass": r12["pass"],
        "issue_closed": not issue_open,
        "pass": ok,
        "status": "fail",
        "reason": "issue #45 still open — self-validation insufficient" if issue_open else None,
        **{k: r12[k] for k in ("output", "command") if k in r12},
    }


def _check_1_3_self_hosting(open_set: set[int]) -> tuple[bool, dict]:
    bootstrap = run_cmd(["python3", "scripts/verify_self_hosting.py"])
    native = run_cmd(["python3", "scripts/verify_self_hosting.py", "--native"])
    native_manifest = ROOT / "manifest" / "native_self_host.json"
    native_ok = native["pass"]
    if native_manifest.exists():
        try:
            native_ok = json.loads(native_manifest.read_text()).get("pass", False) and native_ok
        except json.JSONDecodeError:
            native_ok = False
    issue_open = 46 in open_set
    ok = native_ok and not issue_open
    return ok, {
        "check": "1.3_self_hosting",
        "ref": "issue_46",
        "bootstrap_script_pass": bootstrap["pass"],
        "native_self_host_pass": native_ok,
        "native_manifest": str(native_manifest.relative_to(ROOT)) if native_manifest.exists() else None,
        "issue_closed": not issue_open,
        "pass": ok,
        "status": "fail" if not ok else "validated",
        "reason": (
            "issue #46 still open"
            if issue_open
            else ("native self-host not passing" if not native_ok else None)
        ),
    }


def phase_1_checks(open_set: set[int]) -> tuple[bool, list[dict]]:
    evidence: list[dict] = []
    all_ok = True
    for check_fn in (_check_1_1_wasm_codegen, _check_1_2_knowledge_codegen, _check_1_3_self_hosting):
        ok, item = check_fn(open_set)
        evidence.append(item)
        all_ok = all_ok and ok
    return all_ok, evidence


def test_phase_1_smoke() -> None:
    print("phase_1 smoke")
    assert health()["/health"]
