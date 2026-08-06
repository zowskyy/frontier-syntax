#!/usr/bin/env python3
"""
Blueprint tracking gate — independent validator for PROJECT_BLUEPRINT.md.

Exits 0 only when all validated slices pass with evidence.
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

# P0 checks — must all pass for phase_1 gate
P0_CHECKS = [
    ("1.1_wasm_codegen", ["cargo", "test", "--lib", "wasm_codegen::"], "issue_44"),
    ("1.2_knowledge_codegen", ["cargo", "test", "--lib", "wasm_codegen::tests::test_knowledge_changes_wasm"], "issue_45"),
    ("1.3_self_hosting", ["python3", "scripts/verify_self_hosting.py"], "issue_46"),
]

P1_CHECKS = [
    ("2.1_spec_impl", ["python3", "scripts/spec_impl_bridge.py"], "issue_47"),
    ("2.2_lib_tests", ["cargo", "test", "--lib"], "coverage"),
    ("3.1_wasm_size", ["python3", "scripts/optimize_wasm_size.py"], "issue_48"),
]


def run_cmd(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "output": (r.stdout + r.stderr)[-600:],
        "command": " ".join(cmd),
    }


def check_wasm_size_met() -> dict:
    path = ROOT / "manifest" / "wasm_size.json"
    if not path.exists():
        return {"pass": False, "reason": "manifest missing"}
    data = json.loads(path.read_text())
    return {"pass": data.get("met", False), "size_kb": data.get("size_kb"), "target_kb": data.get("target_kb")}


def gate() -> dict:
    evidence: list[dict] = []
    p0_pass = True
    p1_pass = True

    for name, cmd, ref in P0_CHECKS:
        result = run_cmd(cmd)
        entry = {"check": name, "ref": ref, **result}
        if name == "1.3_self_hosting" and result["pass"]:
            entry["status"] = "partial"
            entry["note"] = "Bootstrap wrapper pass — Frontier-native compiler not validated (Phase 5)"
        evidence.append(entry)
        if not result["pass"]:
            p0_pass = False

    for name, cmd, ref in P1_CHECKS:
        result = run_cmd(cmd)
        entry = {"check": name, "ref": ref, **result}
        evidence.append(entry)
        if not result["pass"]:
            p1_pass = False

    size = check_wasm_size_met()
    evidence.append({"check": "3.1_wasm_size_target", "ref": "issue_48", **size})
    if not size["pass"]:
        p1_pass = False

    # Phase 0: tracking files exist
    phase0 = TRACKING.exists() and Path(__file__).exists()

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase_0_ready": phase0,
        "phase_1_p0_pass": p0_pass,
        "phase_2_3_p1_pass": p1_pass,
        "all_pass": p0_pass and p1_pass and phase0,
        "evidence": evidence,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if TRACKING.exists():
        data = json.loads(TRACKING.read_text())
        data["updated_at"] = summary["generated_at"]
        for phase in data.get("phases", []):
            if phase["id"] == "phase_0":
                phase["status"] = "in_progress" if phase0 else "not_started"
            elif phase["id"] == "phase_1":
                phase["status"] = "validated" if p0_pass else "in_progress"
            elif phase["id"] in ("phase_2", "phase_3"):
                phase["status"] = "validated" if p1_pass and p0_pass else "blocked"
        TRACKING.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return summary


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "gate":
        print("Usage: python3 scripts/tracking.py gate", file=sys.stderr)
        return 2
    summary = gate()
    print(json.dumps({
        "all_pass": summary["all_pass"],
        "phase_1_p0_pass": summary["phase_1_p0_pass"],
        "phase_2_3_p1_pass": summary["phase_2_3_p1_pass"],
        "evidence_file": str(EVIDENCE.relative_to(ROOT)),
    }, indent=2))
    for e in summary["evidence"]:
        icon = "PASS" if e.get("pass") else "FAIL"
        print(f"  [{icon}] {e.get('check')}")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
