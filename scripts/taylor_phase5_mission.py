#!/usr/bin/env python3
"""
Taylor Phase 5 Mission — Gate slice crew (W2 sub-workers).

P5-1 Diagnose  — detect wasm-slim blockers in main.fr
P5-2 Preflight — confirm Gate slice source shape
P5-3 Verify    — run verify_main_fr_native.py (compile(8)==840)
P5-4 ManifestSync — sync main_fr_native.json + M5 gate milestone + ga_status hook

GA protocol: Phase 5 Gate slice is step 1 toward RELEASE_READY, not the finish line.
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
MAIN = ROOT / "frontier" / "src" / "main.fr"
MANIFEST = ROOT / "manifest" / "taylor_phase5_mission.json"
REPORT = ROOT / "audit_reports" / "taylor_phase5_report.md"
MAIN_FR_NATIVE = ROOT / "manifest" / "main_fr_native.json"
GA_STATUS = ROOT / "manifest" / "ga_status.json"

WASM_SLIM_BLOCKERS = (
    "version:",
    "import ",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], timeout: int = 900) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "command": " ".join(cmd),
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output_tail": (r.stdout + r.stderr)[-800:],
    }


def worker_p5_1_diagnose() -> dict[str, Any]:
    if not MAIN.exists():
        return {"id": "P5-1", "name": "Diagnose", "pass": False, "error": f"missing {MAIN}"}
    text = MAIN.read_text(encoding="utf-8")
    blockers = [b for b in WASM_SLIM_BLOCKERS if b in text]
    return {
        "id": "P5-1",
        "name": "Diagnose",
        "pass": len(blockers) == 0,
        "blockers": blockers,
        "source": str(MAIN.relative_to(ROOT)),
    }


def worker_p5_2_preflight() -> dict[str, Any]:
    text = MAIN.read_text(encoding="utf-8") if MAIN.exists() else ""
    has_compile = "fn compile(" in text
    has_main = "fn main()" in text
    return {
        "id": "P5-2",
        "name": "Preflight",
        "pass": has_compile and has_main,
        "has_compile": has_compile,
        "has_main": has_main,
    }


def worker_p5_3_verify() -> dict[str, Any]:
    step = run_cmd([sys.executable, "scripts/verify_main_fr_native.py"])
    manifest_pass = False
    if MAIN_FR_NATIVE.exists():
        try:
            manifest_pass = bool(json.loads(MAIN_FR_NATIVE.read_text(encoding="utf-8")).get("pass"))
        except json.JSONDecodeError:
            pass
    return {
        "id": "P5-3",
        "name": "Verify",
        "pass": step["pass"] and manifest_pass,
        "verify": step,
        "manifest_pass": manifest_pass,
    }


def worker_p5_4_manifest_sync(gate_pass: bool) -> dict[str, Any]:
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
        "id": "P5-4",
        "name": "ManifestSync",
        "pass": gate_pass,
        "main_fr_native": str(MAIN_FR_NATIVE.relative_to(ROOT)),
        "ga_audit": ga_audit,
        "ga_verdict": ga_verdict,
        "ga_blockers": ga_blockers,
    }


def advance(*, apply: bool = False) -> dict[str, Any]:
    workers = [
        worker_p5_1_diagnose(),
        worker_p5_2_preflight(),
    ]
    if apply or all(w["pass"] for w in workers):
        workers.append(worker_p5_3_verify())
    else:
        workers.append({
            "id": "P5-3",
            "name": "Verify",
            "pass": False,
            "skipped": True,
            "reason": "preflight/diagnose failed",
        })

    gate_pass = workers[-1].get("pass") is True
    workers.append(worker_p5_4_manifest_sync(gate_pass))

    result = {
        "owner": "W2_CompilerCore",
        "slice": "gate",
        "goal": "Phase 5 Gate slice — main.fr native wasmtime → 840",
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
        "# Taylor Phase 5 Mission Report",
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
    p5_4 = next((w for w in result.get("workers", []) if w.get("id") == "P5-4"), {})
    if p5_4.get("ga_verdict"):
        lines.extend([
            "",
            "## GA status",
            "",
            f"- Verdict: `{p5_4.get('ga_verdict')}`",
            f"- Blockers: `{p5_4.get('ga_blockers', [])}`",
        ])
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Phase 5 Gate slice mission")
    p.add_argument("--apply", action="store_true", help="run verify even when preflight warns")
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
