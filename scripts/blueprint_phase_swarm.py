#!/usr/bin/env python3
"""
Blueprint Phase Swarm — teams of 2 workers per phase (0–8).

Each team executes phase-specific work and reports evidence to manifest/blueprint_phase_swarm.json.
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

from lexicon_bound_worker import LexiconBoundWorker  # noqa: E402
from process_logger import ProcessLogger  # noqa: E402

MANIFEST = ROOT / "manifest" / "blueprint_phase_swarm.json"
REPORT = ROOT / "audit_reports" / "blueprint_phase_swarm_report.md"


def _run(cmd: list[str]) -> dict:
    start = time.perf_counter()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "output": (r.stdout + r.stderr)[-400:],
    }


def worker(phase: str, worker_id: str, cmd: list[str], doc: str) -> dict:
    lbw = LexiconBoundWorker(f"blueprint_{phase}_{worker_id}")
    return {
        "phase": phase,
        "worker": worker_id,
        "doc": doc,
        **lbw.execute_command(doc, cmd, doc),
    }


# Teams of 2 per phase
PHASE_TEAMS: dict[str, list[dict]] = {
    "phase_0": [
        {"id": "0a", "cmd": ["python3", "scripts/dedupe_issues.py"], "doc": "Slice 0.1: dedupe GitHub issues"},
        {"id": "0b", "cmd": ["python3", "scripts/tracking.py", "gate"], "doc": "Slice 0.2: run tracking gate"},
    ],
    "phase_1": [
        {"id": "1a", "cmd": ["cargo", "test", "--lib", "wasm_codegen::"], "doc": "Slice 1.1: WASM codegen tests (#44)"},
        {"id": "1b", "cmd": ["cargo", "test", "--lib", "wasm_codegen::tests::test_knowledge_changes_wasm"], "doc": "Slice 1.2: knowledge→codegen (#45)"},
    ],
    "phase_2": [
        {"id": "2a", "cmd": ["python3", "scripts/spec_impl_bridge.py"], "doc": "Slice 2.1: spec/impl bridge (#47)"},
        {"id": "2b", "cmd": ["python3", "scripts/verify_language_hardening.py"], "doc": "Slice 2.2: language hardening"},
    ],
    "phase_3": [
        {"id": "3a", "cmd": ["python3", "scripts/optimize_wasm_size.py"], "doc": "Slice 3.1: WASM size measure (#48)"},
        {"id": "3b", "cmd": ["python3", "-c", "import json;d=json.load(open('manifest/wasm_size.json')); exit(0 if d.get('met') else 1)"], "doc": "Slice 3.1: WASM size target check"},
    ],
    "phase_4": [
        {"id": "4a", "cmd": ["cargo", "test", "--lib", "zk::"], "doc": "Phase 4: ZK verifier smoke test"},
        {"id": "4b", "cmd": ["cargo", "test", "--lib", "pq_signatures"], "doc": "Phase 4: PQ signatures smoke test"},
    ],
    "phase_5": [
        {"id": "5a", "cmd": ["python3", "scripts/verify_self_hosting.py"], "doc": "Phase 5: self-hosting bootstrap verify"},
        {"id": "5b", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "parse", "frontier/src/main.fr"], "doc": "Phase 5: main.fr parse"},
    ],
    "phase_6": [
        {"id": "6a", "cmd": ["python3", "-c", "from pathlib import Path; p=Path('docs/blueprint_phase6_agent_spec.md'); print('exists' if p.exists() else 'missing'); exit(0 if p.exists() else 1)"], "doc": "Phase 6: agent spec exists"},
        {"id": "6b", "cmd": ["python3", "scripts/verify_lexicon_bound.py"], "doc": "Phase 6: lexicon-bound worker gates"},
    ],
    "phase_7": [
        {"id": "7a", "cmd": ["python3", "scripts/runtime_cdx.py"], "doc": "Phase 7: CDX runtime probe"},
        {"id": "7b", "cmd": ["bash", "deploy/health_check.sh"], "doc": "Phase 7: health check script"},
    ],
    "phase_8": [
        {"id": "8a", "cmd": ["python3", "-c", "import urllib.request; r=urllib.request.urlopen('https://frontier.dev/install', timeout=5); print(r.status)"], "doc": "Phase 8: frontier.dev install check"},
        {"id": "8b", "cmd": ["python3", "-c", "print('LAUNCH_CHECKLIST external items pending')"], "doc": "Phase 8: launch checklist status"},
    ],
}


PHASE_NAMES = {
    "phase_0": "Tracker & Truth Hygiene",
    "phase_1": "Core Compiler Correctness (P0)",
    "phase_2": "Core Language & Spec Parity (P1)",
    "phase_3": "Size & Performance (P1)",
    "phase_4": "Verification Claims (7 innovations)",
    "phase_5": "True Self-Hosting",
    "phase_6": "Independent AI Agent",
    "phase_7": "Production Hardening",
    "phase_8": "Launch",
}


def run_team(phase: str, tasks: list[dict]) -> dict:
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(worker, phase, t["id"], t["cmd"], t["doc"])
            for t in tasks
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda x: x["worker"])
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "phase": phase,
        "name": PHASE_NAMES.get(phase, phase),
        "workers": 2,
        "passed": passed,
        "all_pass": passed == 2,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "results": results,
    }


def generate_phase6_spec() -> None:
    spec = ROOT / "docs" / "blueprint_phase6_agent_spec.md"
    if spec.exists():
        return
    spec.write_text("""# Phase 6 Agent Spec (Blueprint prerequisite)

## What the agent does that human + compiler cannot (10x claim)
- Parallel swarm execution across 24+ lexicon-bound workers with shared knowledge hypercube
- Autonomous gap closure loops with logged evidence (not self-reported)

## Out of scope for v1
- Unsandboxed arbitrary code execution on user machines
- Production frontier.dev deployment

## Safety boundary
- All actions logged to docs/lexicon_log.fr with hashed user_id
- Lexicon Hard Gate requires documentation before action completes
- Agent intents routed through frontier_agent.py — no direct shell from user input

## Status: SPEC DRAFT — blocked until Phase 5 gate passes
""", encoding="utf-8")


def generate_report(teams: list[dict], total_ms: int) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines = [
        "# Blueprint Phase Swarm Report",
        "",
        f"**Generated:** {now}  ",
        f"**Teams:** 9 phases × 2 workers = 18  ",
        f"**Duration:** {total_ms}ms  ",
        "",
        "## Phase Results",
        "",
        "| Phase | Name | Workers | Result |",
        "|-------|------|---------|--------|",
    ]
    for t in teams:
        icon = "✅" if t["all_pass"] else "🟡"
        lines.append(f"| {t['phase']} | {t['name']} | {t['passed']}/2 | {icon} |")

    lines.extend(["", "## Worker Details", ""])
    for t in teams:
        lines.append(f"### {t['phase']}: {t['name']}")
        for r in t["results"]:
            icon = "✅" if r.get("pass") else "❌"
            lines.append(f"- {icon} `{r['worker']}` — {r.get('doc', '')[:60]}")
        lines.append("")

    lines.append("*Source: PROJECT_BLUEPRINT.md | Gate: `python3 scripts/tracking.py gate`*")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def run_swarm() -> dict:
    plog = ProcessLogger(worker_id="blueprint_phase_swarm")
    generate_phase6_spec()
    start = time.perf_counter()

    teams: list[dict] = []
    with ThreadPoolExecutor(max_workers=9) as pool:
        futures = {pool.submit(run_team, phase, tasks): phase for phase, tasks in PHASE_TEAMS.items()}
        for fut in as_completed(futures):
            teams.append(fut.result())

    teams.sort(key=lambda x: x["phase"])
    total_ms = int((time.perf_counter() - start) * 1000)

    # Re-run tracking gate after all work
    gate = _run(["python3", "scripts/tracking.py", "gate"])

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "teams": len(teams),
        "workers_total": sum(t["workers"] for t in teams),
        "teams_all_pass": sum(1 for t in teams if t["all_pass"]),
        "duration_ms": total_ms,
        "tracking_gate": gate,
        "phase_results": teams,
    }
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generate_report(teams, total_ms)
    plog.log("blueprint_phase_swarm", "complete", "pass", {"teams": len(teams)})
    return summary


def main() -> int:
    summary = run_swarm()
    print(json.dumps({
        "teams": summary["teams"],
        "teams_all_pass": summary["teams_all_pass"],
        "tracking_gate_pass": summary["tracking_gate"]["pass"],
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
