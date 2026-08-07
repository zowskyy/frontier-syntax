#!/usr/bin/env python3
"""
Taylor Phase 6 Mission — training corpus Gate slice crew (W2 sub-workers).

P6-1 Diagnose  — corpus paths, sample count, script ROOT sanity
P6-2 Preflight — validate_sample + generate_corpus present
P6-3 Verify    — run verify_phase6_corpus.py → phase6_corpus_verify.json
P6-4 ManifestSync — GA audit hook

GA protocol: Phase 6 Gate slice advances wave_3_phase4_validated.
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
CORPUS_JSONL = ROOT / "manifest" / "training_corpus" / "frontier_v1.jsonl"
CORPUS_STATS = ROOT / "manifest" / "training_corpus" / "stats.json"
PHASE6_MANIFEST = ROOT / "manifest" / "phase6_corpus_verify.json"
MANIFEST = ROOT / "manifest" / "taylor_phase6_mission.json"
REPORT = ROOT / "audit_reports" / "taylor_phase6_report.md"
GA_STATUS = ROOT / "manifest" / "ga_status.json"
MIN_SAMPLES = 1000

VALIDATE_CORPUS = ROOT / "scripts" / "training" / "validate_corpus.py"
VALIDATE_SAMPLE = ROOT / "scripts" / "training" / "validate_sample.py"
GENERATE_CORPUS = ROOT / "scripts" / "training" / "generate_corpus.py"


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


def corpus_sample_count() -> int:
    if not CORPUS_JSONL.exists():
        return 0
    return sum(1 for line in CORPUS_JSONL.read_text(encoding="utf-8").splitlines() if line.strip())


def worker_p6_1_diagnose() -> dict[str, Any]:
    blockers: list[str] = []
    if not VALIDATE_CORPUS.exists():
        blockers.append("missing scripts/training/validate_corpus.py")

    count = corpus_sample_count()
    if count < MIN_SAMPLES:
        blockers.append(f"corpus sample_count {count} < {MIN_SAMPLES}")

    return {
        "id": "P6-1",
        "name": "Diagnose",
        "pass": len(blockers) == 0,
        "blockers": blockers,
        "sample_count": count,
        "min_samples": MIN_SAMPLES,
        "corpus_jsonl": str(CORPUS_JSONL.relative_to(ROOT)),
    }


def worker_p6_2_preflight() -> dict[str, Any]:
    scripts_ok = all(p.exists() for p in (VALIDATE_CORPUS, VALIDATE_SAMPLE, GENERATE_CORPUS))
    stats_ok = CORPUS_STATS.exists()
    return {
        "id": "P6-2",
        "name": "Preflight",
        "pass": scripts_ok and stats_ok,
        "scripts_ok": scripts_ok,
        "stats_ok": stats_ok,
    }


def worker_p6_3_verify() -> dict[str, Any]:
    step = run_cmd([sys.executable, "scripts/verify_phase6_corpus.py"])
    manifest_pass = False
    if PHASE6_MANIFEST.exists():
        try:
            manifest_pass = bool(json.loads(PHASE6_MANIFEST.read_text(encoding="utf-8")).get("pass"))
        except json.JSONDecodeError:
            pass
    return {
        "id": "P6-3",
        "name": "Verify",
        "pass": step["pass"] and manifest_pass,
        "verify": step,
        "manifest_pass": manifest_pass,
    }


def worker_p6_4_manifest_sync(gate_pass: bool) -> dict[str, Any]:
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
        "id": "P6-4",
        "name": "ManifestSync",
        "pass": gate_pass,
        "phase6_manifest": str(PHASE6_MANIFEST.relative_to(ROOT)),
        "ga_audit": ga_audit,
        "ga_verdict": ga_verdict,
        "ga_blockers": ga_blockers,
    }


def advance(*, apply: bool = False) -> dict[str, Any]:
    workers: list[dict[str, Any]] = [
        worker_p6_1_diagnose(),
        worker_p6_2_preflight(),
    ]
    if apply or all(w["pass"] for w in workers):
        workers.append(worker_p6_3_verify())
    else:
        workers.append({
            "id": "P6-3",
            "name": "Verify",
            "pass": False,
            "skipped": True,
            "reason": "preflight/diagnose failed",
        })

    gate_pass = workers[-1].get("pass") is True
    workers.append(worker_p6_4_manifest_sync(gate_pass))

    result = {
        "owner": "W2_CompilerCore",
        "slice": "gate",
        "goal": "Phase 6 Gate slice — training corpus compile + wasmtime spot-check",
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
        "# Taylor Phase 6 Mission Report",
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
    p6_4 = next((w for w in result.get("workers", []) if w.get("id") == "P6-4"), {})
    if p6_4.get("ga_verdict"):
        lines.extend([
            "",
            "## GA status",
            "",
            f"- Verdict: `{p6_4.get('ga_verdict')}`",
            f"- Blockers: `{p6_4.get('ga_blockers', [])}`",
        ])
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Phase 6 Gate slice mission")
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
