#!/usr/bin/env python3
"""
Blueprint Phase Swarm — teams of 2 workers, STRICT SEQUENTIAL ordering.

Only runs phases whose prior gate has passed. Phases 4–8 are FROZEN until phase 3 passes.
No parallel all-phase execution.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from process_logger import ProcessLogger  # noqa: E402
from tracking import gate as tracking_gate  # noqa: E402

MANIFEST = ROOT / "manifest" / "blueprint_phase_swarm.json"
REPORT = ROOT / "audit_reports/blueprint_phase_swarm_report.md"

# Only phases that may run (4–8 never scheduled while frozen)
RUNNABLE_PHASES = ("phase_0", "phase_1", "phase_2", "phase_3")

PHASE_TEAMS: dict[str, list[dict]] = {
    "phase_0": [
        {"id": "0a", "cmd": ["python3", "scripts/dedupe_issues.py"], "doc": "Slice 0.1: dedupe issues"},
        {"id": "0b", "cmd": ["python3", "-c", "import pathlib; r=pathlib.Path('README.md').read_text(); l=pathlib.Path('LAUNCH_CHECKLIST.md').read_text(); exit(0 if 'NOT VERIFIED' in r and 'NOT VERIFIED' in l else 1)"], "doc": "Slice 0.3: NOT VERIFIED markers"},
    ],
    "phase_1": [
        {"id": "1a", "cmd": ["cargo", "test", "--lib", "wasm_codegen::"], "doc": "Slice 1.1: wasm_codegen tests (issue #44 open = not validated)"},
        {"id": "1b", "cmd": ["cargo", "test", "--lib", "wasm_codegen::tests::test_knowledge_changes_wasm"], "doc": "Slice 1.2: knowledge test (issue #45 open = not validated)"},
    ],
    "phase_2": [
        {"id": "2a", "cmd": ["python3", "scripts/spec_impl_bridge.py"], "doc": "Slice 2.1: spec/impl (#47)"},
        {"id": "2b", "cmd": ["python3", "scripts/verify_language_hardening.py"], "doc": "Slice 2.2: language hardening"},
    ],
    "phase_3": [
        {"id": "3a", "cmd": ["python3", "scripts/measure_wasm_size.py"], "doc": "Slice 3.1: canonical WASM measure"},
        {"id": "3b", "cmd": ["python3", "-c", "import json; d=json.load(open('manifest/wasm_size.json')); print(d); exit(0 if d.get('met') else 1)"], "doc": "Slice 3.1: target <100 KB"},
    ],
}

PHASE_NAMES = {
    "phase_0": "Tracker & Truth Hygiene",
    "phase_1": "Core Compiler (P0) — issues must be closed to validate",
    "phase_2": "Spec Parity (P1)",
    "phase_3": "WASM Size (P1)",
    "phase_4": "FROZEN — innovations",
    "phase_5": "FROZEN — true self-hosting",
    "phase_6": "FROZEN — AI agent",
    "phase_7": "FROZEN — production",
    "phase_8": "FROZEN — launch",
}


def _run(cmd: list[str]) -> dict:
    start = time.perf_counter()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "output": (r.stdout + r.stderr)[-300:],
    }


def run_team(phase: str) -> dict:
    tasks = PHASE_TEAMS[phase]
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_run, t["cmd"]) for t in tasks]
        for t, fut in zip(tasks, futures):
            r = fut.result()
            results.append({"worker": t["id"], "doc": t["doc"], **r})
    # Phase validation from tracking gate, not raw worker pass alone
    gate_json = tracking_gate()
    gate_map = {"phase_0": "phase_0_pass", "phase_1": "phase_1_pass", "phase_2": "phase_2_pass", "phase_3": "phase_3_pass"}
    validated = bool(gate_json.get(gate_map.get(phase, ""), False))
    return {
        "phase": phase,
        "name": PHASE_NAMES[phase],
        "workers": results,
        "workers_cmd_pass": sum(1 for r in results if r["pass"]),
        "phase_validated": validated,
        "status": "validated" if validated else "fail",
        "duration_ms": int((time.perf_counter() - start) * 1000),
    }


def run_swarm() -> dict:
    plog = ProcessLogger(worker_id="blueprint_phase_swarm")
    start = time.perf_counter()
    teams: list[dict] = []
    stopped_at: str | None = None

    for phase in RUNNABLE_PHASES:
        team = run_team(phase)
        teams.append(team)
        plog.log(phase, "team_run", team["status"], {"validated": team["phase_validated"]})
        if not team["phase_validated"]:
            stopped_at = phase
            break

    frozen = [
        {"phase": f"phase_{i}", "name": PHASE_NAMES[f"phase_{i}"], "status": "frozen", "workers": 0, "reason": "Prior gate not passed"}
        for i in range(4, 9)
    ]

    gate_summary = tracking_gate()

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "sequential_strict",
        "frozen_phases": ["phase_4", "phase_5", "phase_6", "phase_7", "phase_8"],
        "stopped_at": stopped_at,
        "teams_run": len(teams),
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "phase_results": teams,
        "frozen": frozen,
        "tracking_gate_all_pass": gate_summary.get("all_pass", False),
    }
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generate_report(summary)
    return summary


def generate_report(summary: dict) -> None:
    lines = [
        "# Blueprint Phase Swarm Report (Strict Sequential)",
        "",
        f"**Generated:** {summary['generated_at']}",
        f"**Mode:** sequential — stopped at `{summary.get('stopped_at', 'complete')}`",
        f"**Phases 4–8:** FROZEN (not executed)",
        "",
        "## Results",
        "",
        "| Phase | Gate validated | Worker cmds |",
        "|-------|----------------|-------------|",
    ]
    for t in summary.get("phase_results", []):
        icon = "✅" if t.get("phase_validated") else "❌"
        wp = t.get("workers_cmd_pass", 0)
        lines.append(f"| {t['phase']} | {icon} {t.get('status')} | {wp}/2 cmds pass |")
    for f in summary.get("frozen", []):
        lines.append(f"| {f['phase']} | 🔒 frozen | — |")
    lines.extend([
        "",
        "## Rules enforced",
        "",
        "- No partial credit on 1.3 self-hosting (bootstrap ≠ pass)",
        "- Issues #44–48 must be closed to validate P0/P1 slices",
        "- WASM size: `scripts/measure_wasm_size.py` → `manifest/wasm_size.json` only",
        "- Phases 4–6 not touched while phase 3 fails",
        "",
        "*Gate: `python3 scripts/tracking.py gate`*",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    summary = run_swarm()
    print(json.dumps({
        "mode": "sequential_strict",
        "stopped_at": summary.get("stopped_at"),
        "frozen_phases": summary.get("frozen_phases"),
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
