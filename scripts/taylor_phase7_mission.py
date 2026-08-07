#!/usr/bin/env python3
"""
Taylor Phase 7 Mission — production hardening Gate slice crew (W2 sub-workers).

P7-1 Diagnose  — clippy + agent security scripts present
P7-2 Preflight — compiler-gate.yml + phase6 manifest green
P7-3 Verify    — run verify_phase7_hardening.py → phase7_hardening_verify.json
P7-4 ManifestSync — GA audit hook

GA protocol: Phase 7 Gate slice advances wave_3_phase4_validated.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PHASE7_MANIFEST = ROOT / "manifest" / "phase7_hardening_verify.json"
PHASE6_MANIFEST = ROOT / "manifest" / "phase6_corpus_verify.json"
MANIFEST = ROOT / "manifest" / "taylor_phase7_mission.json"
REPORT = ROOT / "audit_reports" / "taylor_phase7_report.md"
GA_STATUS = ROOT / "manifest" / "ga_status.json"
COMPILER_CI = ROOT / ".github" / "workflows" / "compiler-gate.yml"
AGENT_SECURITY = ROOT / "scripts" / "verify_agent_security.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], timeout: int = 1800) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "command": " ".join(cmd),
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output_tail": (r.stdout + r.stderr)[-800:],
    }


def worker_p7_1_diagnose() -> dict[str, Any]:
    blockers: list[str] = []
    if not AGENT_SECURITY.exists():
        blockers.append("missing scripts/verify_agent_security.py")
    if not COMPILER_CI.exists():
        blockers.append("missing .github/workflows/compiler-gate.yml")
    return {
        "id": "P7-1",
        "name": "Diagnose",
        "pass": len(blockers) == 0,
        "blockers": blockers,
    }


def worker_p7_2_preflight() -> dict[str, Any]:
    phase6_pass = False
    if PHASE6_MANIFEST.exists():
        try:
            phase6_pass = bool(json.loads(PHASE6_MANIFEST.read_text(encoding="utf-8")).get("pass"))
        except json.JSONDecodeError:
            pass
    return {
        "id": "P7-2",
        "name": "Preflight",
        "pass": phase6_pass,
        "phase6_pass": phase6_pass,
        "phase6_manifest": str(PHASE6_MANIFEST.relative_to(ROOT)),
    }


def worker_p7_3_verify() -> dict[str, Any]:
    step = run_cmd([sys.executable, "scripts/verify_phase7_hardening.py"])
    manifest_pass = False
    if PHASE7_MANIFEST.exists():
        try:
            manifest_pass = bool(json.loads(PHASE7_MANIFEST.read_text(encoding="utf-8")).get("pass"))
        except json.JSONDecodeError:
            pass
    return {
        "id": "P7-3",
        "name": "Verify",
        "pass": step["pass"] and manifest_pass,
        "verify": step,
        "manifest_pass": manifest_pass,
    }


def worker_p7_4_manifest_sync(gate_pass: bool) -> dict[str, Any]:
    ga_audit = run_cmd([sys.executable, "scripts/release_readiness.py", "--audit", "--skip-run"])
    ga_verdict = None
    ga_blockers: list[str] = []
    if GA_STATUS.exists():
        try:
            ga = json.loads(GA_STATUS.read_text(encoding="utf-8"))
            ga_verdict = ga.get("verdict")
            ga_blockers = ga.get("blockers", [])
        except json.JSONDecodeError:
            pass
    return {
        "id": "P7-4",
        "name": "ManifestSync",
        "pass": gate_pass,
        "phase7_manifest": str(PHASE7_MANIFEST.relative_to(ROOT)),
        "ga_audit": ga_audit,
        "ga_verdict": ga_verdict,
        "ga_blockers": ga_blockers,
    }


def advance(*, apply: bool = False) -> dict[str, Any]:
    workers: list[dict[str, Any]] = [
        worker_p7_1_diagnose(),
        worker_p7_2_preflight(),
    ]
    if apply or all(w["pass"] for w in workers):
        workers.append(worker_p7_3_verify())
    else:
        workers.append({
            "id": "P7-3",
            "name": "Verify",
            "pass": False,
            "skipped": True,
            "reason": "preflight/diagnose failed",
        })

    gate_pass = workers[-1].get("pass") is True
    workers.append(worker_p7_4_manifest_sync(gate_pass))

    result = {
        "owner": "W2_CompilerCore",
        "slice": "gate",
        "goal": "Phase 7 Gate slice — clippy, agent security, gate stability",
        "ga_target": "RELEASE_READY",
        "complete": gate_pass,
        "updated_at": utc_now(),
        "apply": apply,
        "workers": workers,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    return result


def write_report(result: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Taylor Phase 7 Mission Report",
        "",
        f"**Updated:** {result.get('updated_at')}  ",
        f"**Gate slice complete:** {result.get('complete')}  ",
        f"**GA target:** `{result.get('ga_target')}`  ",
        "",
        "## Workers",
        "",
        "| ID | Name | Pass |",
        "|----|------|------|",
    ]
    for w in result.get("workers", []):
        lines.append(f"| {w['id']} | {w['name']} | {'PASS' if w.get('pass') else 'FAIL'} |")
    p7_4 = next((w for w in result.get("workers", []) if w.get("id") == "P7-4"), {})
    if p7_4.get("ga_verdict"):
        lines.extend([
            "",
            "## GA status",
            "",
            f"- Verdict: `{p7_4.get('ga_verdict')}`",
            f"- Blockers: `{p7_4.get('ga_blockers', [])}`",
        ])
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Phase 7 Gate slice mission")
    p.add_argument("--apply", action="store_true", help="run verify after diagnose/preflight")
    args = p.parse_args()
    result = advance(apply=args.apply)
    print(json.dumps({
        "complete": result["complete"],
        "ga_target": result["ga_target"],
        "workers": {w["id"]: w.get("pass") for w in result.get("workers", [])},
        "report": str(REPORT.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
    }, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
