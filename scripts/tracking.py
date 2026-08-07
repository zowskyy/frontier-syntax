#!/usr/bin/env python3
"""
Blueprint tracking gate — strict ordering, no partial credit.

Rules (PROJECT_BLUEPRINT.md):
- Phase N is not evaluated until phase N-1 is validated.
- Phases 4–8 are FROZEN until phase 3 gate passes.
- Issue #44–48 must be CLOSED for P0/P1 slices to validate (no self-validation).
- 1.3_self_hosting FAILS while bootstrap wrapper is required (Phase 5 criterion).
- WASM size: manifest/wasm_size.json from scripts/measure_wasm_size.py only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING = ROOT / "TRACKING.json"
EVIDENCE = ROOT / "manifest" / "tracking_evidence.json"

CANONICAL_ISSUES = {44, 45, 46, 47, 48}
FROZEN_FROM_PHASE = 4


def read_manifest(path: Path, field: str, expected=True) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(field) == expected
    except json.JSONDecodeError:
        return False


def run_cmd(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "output": (r.stdout + r.stderr)[-600:],
        "command": " ".join(cmd),
    }


def open_issues() -> set[int]:
    r = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--json",
            "number",
            "--exclude-pull-requests",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return CANONICAL_ISSUES  # conservative: assume all open if gh fails
    return {i["number"] for i in json.loads(r.stdout)}


def phase_0_checks() -> tuple[bool, list[dict]]:
    evidence = []
    open_set = open_issues()
    dedupe_ok = open_set <= CANONICAL_ISSUES and len(open_set) <= 5
    evidence.append({
        "check": "0.1_issue_dedupe",
        "pass": dedupe_ok,
        "open_issues": sorted(open_set),
        "expected": sorted(CANONICAL_ISSUES),
    })
    gate_exists = Path(__file__).exists() and TRACKING.exists()
    evidence.append({"check": "0.2_gate_exists", "pass": gate_exists})
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    launch = (ROOT / "LAUNCH_CHECKLIST.md").read_text(encoding="utf-8") if (ROOT / "LAUNCH_CHECKLIST.md").exists() else ""
    claims_ok = (
        "VALIDATED" in readme
        and "VALIDATED" in launch
        and "NOT VERIFIED" in launch  # honest marker for Phase 4+ still required
    )
    evidence.append({"check": "0.3_public_claims", "pass": claims_ok})
    return all(e["pass"] for e in evidence), evidence


def phase_1_checks(open_set: set[int]) -> tuple[bool, list[dict]]:
    evidence = []
    all_ok = True

    r11 = run_cmd(["cargo", "test", "--lib", "-p", "frontier", "wasm_codegen::"])
    r11_exec = run_cmd(["python3", "scripts/verify_wasm_codegen.py"])
    issue_open = 44 in open_set
    ok = r11["pass"] and r11_exec["pass"] and not issue_open
    evidence.append({
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
    })
    if not ok:
        all_ok = False

    r12 = run_cmd(["cargo", "test", "--lib", "-p", "frontier", "wasm_codegen::tests::test_knowledge_changes_wasm"])
    issue_open = 45 in open_set
    ok = r12["pass"] and not issue_open
    evidence.append({
        "check": "1.2_knowledge_codegen",
        "ref": "issue_45",
        "tests_pass": r12["pass"],
        "issue_closed": not issue_open,
        "pass": ok,
        "status": "fail",
        "reason": "issue #45 still open — self-validation insufficient" if issue_open else None,
        **{k: r12[k] for k in ("output", "command") if k in r12},
    })
    if not ok:
        all_ok = False

    # 1.3: native wasmtime self-host (bootstrap alone is informational only)
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
    evidence.append({
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
    })
    if not ok:
        all_ok = False

    return all_ok, evidence


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


def phase_4_checks(phase_3_ok: bool) -> tuple[bool, list[dict]]:
    if not phase_3_ok:
        return False, [{"check": "phase_4", "pass": False, "status": "blocked", "reason": "phase_3 not validated"}]
    evidence = []
    r = run_cmd(["python3", "scripts/verify_innovations.py"])
    manifest_ok = read_manifest(ROOT / "manifest" / "innovations_verify.json", "pass")
    ok = r["pass"] and manifest_ok
    evidence.append({
        "check": "4.1_innovations",
        "pass": ok,
        "status": "validated" if ok else "fail",
        "manifest": "manifest/innovations_verify.json",
        **r,
    })
    return ok, evidence


def phase_5_checks(phase_4_ok: bool) -> tuple[bool, list[dict]]:
    if not phase_4_ok:
        return False, [{"check": "phase_5", "pass": False, "status": "blocked", "reason": "phase_4 not validated"}]
    evidence = []
    r = run_cmd(["python3", "scripts/verify_main_fr_native.py"])
    manifest_ok = read_manifest(ROOT / "manifest" / "main_fr_native.json", "pass")
    ok = r["pass"] and manifest_ok
    evidence.append({
        "check": "5.1_main_fr_native",
        "pass": ok,
        "status": "validated" if ok else "fail",
        "manifest": "manifest/main_fr_native.json",
        **r,
    })
    return ok, evidence


def phase_6_checks(phase_5_ok: bool) -> tuple[bool, list[dict]]:
    if not phase_5_ok:
        return False, [{"check": "phase_6", "pass": False, "status": "blocked", "reason": "phase_5 not validated"}]
    evidence = []
    r = run_cmd(["python3", "scripts/verify_phase6_corpus.py"])
    manifest_ok = read_manifest(ROOT / "manifest" / "phase6_corpus_verify.json", "pass")
    ok = r["pass"] and manifest_ok
    evidence.append({
        "check": "6.1_training_corpus",
        "pass": ok,
        "status": "validated" if ok else "fail",
        "manifest": "manifest/phase6_corpus_verify.json",
        **r,
    })
    return ok, evidence


def phase_7_checks(phase_6_ok: bool) -> tuple[bool, list[dict]]:
    if not phase_6_ok:
        return False, [{"check": "phase_7", "pass": False, "status": "blocked", "reason": "phase_6 not validated"}]
    evidence = []
    r = run_cmd(["python3", "scripts/verify_phase7_hardening.py"])
    manifest_ok = read_manifest(ROOT / "manifest" / "phase7_hardening_verify.json", "pass")
    ok = r["pass"] and manifest_ok
    evidence.append({
        "check": "7.1_production_hardening",
        "pass": ok,
        "status": "validated" if ok else "fail",
        "manifest": "manifest/phase7_hardening_verify.json",
        **r,
    })
    return ok, evidence


def read_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def frozen_phases_report(from_phase: int) -> list[dict]:
    return [
        {
            "check": f"phase_{p}",
            "pass": False,
            "status": "frozen",
            "reason": f"FROZEN until phase_{p - 1} gate passes",
        }
        for p in range(from_phase, 9)
    ]


def phase_8_checks(phase_7_ok: bool) -> tuple[bool, list[dict]]:
    if not phase_7_ok:
        return False, [{"check": "phase_8", "pass": False, "status": "blocked", "reason": "phase_7 not validated"}]
    evidence = []
    r = run_cmd(["python3", "scripts/verify_phase8_launch.py", "--skip-url-check"])
    manifest_ok = read_manifest(ROOT / "manifest" / "phase8_launch_verify.json", "pass")
    ok = r["pass"] and manifest_ok
    evidence.append({
        "check": "8.1_launch",
        "pass": ok,
        "status": "validated" if ok else "fail",
        "manifest": "manifest/phase8_launch_verify.json",
        **r,
    })
    return ok, evidence


def gate(max_phase: int = 8) -> dict:
    evidence: list[dict] = []

    p0_ok, e0 = phase_0_checks()
    evidence.extend(e0)

    open_set = open_issues()

    p1_ok = False
    if p0_ok:
        p1_ok, e1 = phase_1_checks(open_set)
        evidence.extend(e1)
    else:
        evidence.append({"check": "phase_1", "pass": False, "status": "blocked", "reason": "phase_0 incomplete"})

    p2_ok = False
    if p0_ok and p1_ok:
        p2_ok, e2 = phase_2_checks(p1_ok, open_set)
        evidence.extend(e2)
    elif p0_ok:
        evidence.append({"check": "phase_2", "pass": False, "status": "blocked", "reason": "phase_1 not validated"})

    p3_ok = False
    if p0_ok and p1_ok and p2_ok:
        p3_ok, e3 = phase_3_checks(p2_ok, open_set)
        evidence.extend(e3)
    elif p0_ok:
        evidence.append({"check": "phase_3", "pass": False, "status": "blocked", "reason": "phase_2 not validated"})

    p4_ok = p5_ok = p6_ok = p7_ok = p8_ok = False
    if p0_ok and p1_ok and p2_ok and p3_ok and max_phase >= 4:
        p4_ok, e4 = phase_4_checks(p3_ok)
        evidence.extend(e4)
        if p4_ok and max_phase >= 5:
            p5_ok, e5 = phase_5_checks(p4_ok)
            evidence.extend(e5)
        elif max_phase >= 5:
            evidence.append({"check": "phase_5", "pass": False, "status": "blocked", "reason": "phase_4 not validated"})
        if p4_ok and p5_ok and max_phase >= 6:
            p6_ok, e6 = phase_6_checks(p5_ok)
            evidence.extend(e6)
        elif max_phase >= 6:
            evidence.append({"check": "phase_6", "pass": False, "status": "blocked", "reason": "phase_5 not validated"})
        if p4_ok and p5_ok and p6_ok and max_phase >= 7:
            p7_ok, e7 = phase_7_checks(p6_ok)
            evidence.extend(e7)
        elif max_phase >= 7:
            evidence.append({"check": "phase_7", "pass": False, "status": "blocked", "reason": "phase_6 not validated"})
        if p4_ok and p5_ok and p6_ok and p7_ok and max_phase >= 8:
            p8_ok, e8 = phase_8_checks(p7_ok)
            evidence.extend(e8)
        elif max_phase >= 8:
            evidence.append({"check": "phase_8", "pass": False, "status": "blocked", "reason": "phase_7 not validated"})
        if max_phase < 8:
            evidence.extend(frozen_phases_report(max(4, max_phase + 1)))
    elif p0_ok and p1_ok and p2_ok:
        if max_phase < 4:
            evidence.extend(frozen_phases_report(4))
    elif p0_ok:
        evidence.extend(frozen_phases_report(FROZEN_FROM_PHASE))

    if max_phase >= 8:
        all_pass = p0_ok and p1_ok and p2_ok and p3_ok and p4_ok and p5_ok and p6_ok and p7_ok and p8_ok
    elif max_phase == 7:
        all_pass = p0_ok and p1_ok and p2_ok and p3_ok and p4_ok and p5_ok and p6_ok and p7_ok
    elif max_phase == 3:
        all_pass = p0_ok and p1_ok and p2_ok and p3_ok
    else:
        all_pass = p0_ok and p1_ok and p2_ok and p3_ok

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase_0_pass": p0_ok,
        "phase_1_pass": p1_ok,
        "phase_2_pass": p2_ok,
        "phase_3_pass": p3_ok,
        "phase_4_pass": p4_ok,
        "phase_5_pass": p5_ok,
        "phase_6_pass": p6_ok,
        "phase_7_pass": p7_ok,
        "phase_8_pass": p8_ok if max_phase >= 8 else None,
        "max_phase": max_phase,
        "phases_8": "validated" if p8_ok else ("frozen" if p7_ok and max_phase >= 8 else "blocked"),
        "all_pass": all_pass,
        "open_issues": sorted(open_set),
        "no_partial_credit": True,
        "evidence": evidence,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if TRACKING.exists():
        data = json.loads(TRACKING.read_text())
        data["updated_at"] = summary["generated_at"]
        status_map = {
            "phase_0": "validated" if p0_ok else "in_progress",
            "phase_1": "validated" if p1_ok else "fail",
            "phase_2": "validated" if p2_ok else ("blocked" if not p1_ok else "fail"),
            "phase_3": "validated" if p3_ok else ("blocked" if not p2_ok else "fail"),
            "phase_4": "validated" if p4_ok else ("blocked" if not p3_ok else "fail"),
            "phase_5": "validated" if p5_ok else ("blocked" if not p4_ok else "fail"),
            "phase_6": "validated" if p6_ok else ("blocked" if not p5_ok else "fail"),
            "phase_7": "validated" if p7_ok else ("blocked" if not p6_ok else "fail"),
            "phase_8": "validated" if p8_ok else ("blocked" if not p7_ok else ("frozen" if max_phase < 8 else "fail")),
        }
        if max_phase < 8:
            status_map["phase_8"] = "frozen"
        for phase in data.get("phases", []):
            pid = phase["id"]
            if pid in status_map:
                phase["status"] = status_map[pid]
        data["frozen_phases"] = [p for p, st in status_map.items() if st == "frozen"]
        TRACKING.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return summary


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Blueprint tracking gate")
    parser.add_argument("command", nargs="?", default="gate")
    parser.add_argument("--max-phase", type=int, default=8, help="Highest phase to evaluate (blueprint gate uses 3)")
    args = parser.parse_args()
    if args.command != "gate":
        print("Usage: python3 scripts/tracking.py gate [--max-phase N]", file=sys.stderr)
        return 2
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
        if e.get("status") == "frozen":
            print(f"  [FROZEN] {e.get('check')}")
        else:
            icon = "PASS" if e.get("pass") else "FAIL"
            print(f"  [{icon}] {e.get('check')}" + (f" — {e.get('reason')}" if e.get("reason") else ""))
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
