#!/usr/bin/env python3
"""
Execute Peerless Implementation Plan — 4 teams × 6 Frontier workers (24 total).

Teams merge plan items and execute verifiable Frontier actions in parallel.
"""

from __future__ import annotations

import argparse
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

PLAN_MANIFEST = ROOT / "manifest" / "peerless_implementation_plan.json"
EXEC_MANIFEST = ROOT / "manifest" / "peerless_plan_execution.json"
REPORT = ROOT / "audit_reports" / "peerless_plan_execution_report.md"

TEAMS = ("alpha", "beta", "gamma", "delta")
WORKERS_PER_TEAM = 6


def _run(cmd: list[str]) -> dict:
    start = time.perf_counter()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "output": (r.stdout + r.stderr)[-400:],
        "command": " ".join(cmd),
    }


# 24 workers: 4 teams × 6 — each maps to a plan item + executable action
WORKER_TASKS: dict[str, list[dict]] = {
    "alpha": [
        {"id": "A1", "plan_id": "OPT-001", "theme": "wasm_optimization", "label": "wasm_build", "cmd": ["python3", "scripts/optimize_wasm_size.py"]},
        {"id": "A2", "plan_id": "OPT-001", "theme": "wasm_optimization", "label": "wasm_manifest", "cmd": ["python3", "-c", "import json; p=__import__('pathlib').Path('manifest/wasm_size.json'); print(json.loads(p.read_text()) if p.exists() else 'missing')"]},
        {"id": "A3", "plan_id": "OPT-002", "theme": "self_hosting", "label": "self_host_verify", "cmd": ["python3", "scripts/verify_self_hosting.py"]},
        {"id": "A4", "plan_id": "OPT-002", "theme": "self_hosting", "label": "main_fr_parse", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "parse", "frontier/src/main.fr"]},
        {"id": "A5", "plan_id": "OPT-003", "theme": "codegen_depth", "label": "wasm_codegen_tests", "cmd": ["cargo", "test", "--lib", "wasm_codegen::"]},
        {"id": "A6", "plan_id": "OPT-003", "theme": "codegen_depth", "label": "unity_wasm_tests", "cmd": ["cargo", "test", "--lib", "unity::"]},
    ],
    "beta": [
        {"id": "B1", "plan_id": "OPT-004", "theme": "runtime_gpu", "label": "gpu_runtime", "cmd": ["python3", "scripts/runtime_gpu.py"]},
        {"id": "B2", "plan_id": "OPT-007", "theme": "runtime_cdx", "label": "cdx_runtime", "cmd": ["python3", "scripts/runtime_cdx.py"]},
        {"id": "B3", "plan_id": "OPT-008", "theme": "runtime_ipfs", "label": "ipfs_runtime", "cmd": ["python3", "scripts/runtime_ipfs.py"]},
        {"id": "B4", "plan_id": "OPT-004", "theme": "runtime_gpu", "label": "vulkan_module_test", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "run", "frontier/gpu/vulkan.fr", "--test"]},
        {"id": "B5", "plan_id": "OPT-007", "theme": "runtime_cdx", "label": "cdx_module_test", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "run", "frontier/network/cdx_stream.fr", "--test"]},
        {"id": "B6", "plan_id": "OPT-008", "theme": "runtime_ipfs", "label": "ipfs_module_test", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "run", "frontier/ipfs/swarm.fr", "--test"]},
    ],
    "gamma": [
        {"id": "G1", "plan_id": "OPT-005", "theme": "peerless", "label": "close_peerless", "cmd": ["python3", "scripts/close_peerless_gaps.py"]},
        {"id": "G2", "plan_id": "OPT-006", "theme": "swarm_optimization", "label": "peerless_verify", "cmd": ["python3", "scripts/close_peerless_gaps.py", "--verify-only"]},
        {"id": "G3", "plan_id": "OPT-009", "theme": "knowledge_engine", "label": "sync_knowledge", "cmd": ["python3", "scripts/sync_knowledge_base.py"]},
        {"id": "G4", "plan_id": "OPT-010", "theme": "frontier_syntax", "label": "spec_impl_bridge", "cmd": ["python3", "scripts/spec_impl_bridge.py"]},
        {"id": "G5", "plan_id": "OPT-011", "theme": "security", "label": "zk_tests", "cmd": ["cargo", "test", "--lib", "zk::"]},
        {"id": "G6", "plan_id": "OPT-011", "theme": "security", "label": "redos_tests", "cmd": ["python3", "scripts/test_redos.py"]},
    ],
    "delta": [
        {"id": "D1", "plan_id": "OPT-012", "theme": "documentation", "label": "arc_status", "cmd": ["python3", "scripts/generate_arc_status.py"]},
        {"id": "D2", "plan_id": "OPT-013", "theme": "maintenance", "label": "lib_tests", "cmd": ["cargo", "test", "--lib"]},
        {"id": "D3", "plan_id": "OPT-012", "theme": "documentation", "label": "verify_v2", "cmd": ["python3", "scripts/verify_v2.py"]},
        {"id": "D4", "plan_id": "OPT-013", "theme": "maintenance", "label": "language_hardening", "cmd": ["python3", "scripts/verify_language_hardening.py"]},
        {"id": "D5", "plan_id": "OPT-006", "theme": "swarm_optimization", "label": "knowledge_verify", "cmd": ["python3", "scripts/verify_knowledge.py"]},
        {"id": "D6", "plan_id": "OPT-005", "theme": "peerless", "label": "arc_verify", "cmd": ["python3", "build/arc_orchestrator.py", "--verify"]},
    ],
}


def execute_worker(team: str, task: dict, plog: ProcessLogger) -> dict:
    result = _run(task["cmd"])
    entry = {
        "team": team,
        "worker_id": task["id"],
        "plan_id": task["plan_id"],
        "theme": task["theme"],
        "label": task["label"],
        **result,
    }
    plog.log(
        f"team_{team}_{task['id']}",
        f"execute_{task['label']}",
        "pass" if result["pass"] else "fail",
        {"plan_id": task["plan_id"], "duration_ms": result["duration_ms"]},
    )
    return entry


def execute_team(team: str, plog: ProcessLogger) -> dict:
    tasks = WORKER_TASKS[team]
    start = time.perf_counter()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS_PER_TEAM) as pool:
        futures = [pool.submit(execute_worker, team, t, plog) for t in tasks]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda x: x["worker_id"])
    passed = sum(1 for r in results if r["pass"])
    return {
        "team": team,
        "workers": len(results),
        "passed": passed,
        "all_pass": passed == len(results),
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "results": results,
    }


def merge_plan_execution(team_results: list[dict]) -> list[dict]:
    """Merge worker results back onto plan items."""
    if not PLAN_MANIFEST.exists():
        return []
    plan_data = json.loads(PLAN_MANIFEST.read_text(encoding="utf-8"))
    items = {p["plan_id"]: {**p, "execution": {"workers": [], "all_pass": True, "passed": 0, "total": 0}} for p in plan_data.get("plan", [])}

    for tr in team_results:
        for wr in tr.get("results", []):
            pid = wr.get("plan_id")
            if pid not in items:
                continue
            ex = items[pid]["execution"]
            ex["workers"].append({
                "team": wr["team"],
                "worker_id": wr["worker_id"],
                "label": wr["label"],
                "pass": wr["pass"],
                "duration_ms": wr["duration_ms"],
            })
            ex["total"] += 1
            if wr["pass"]:
                ex["passed"] += 1
            else:
                ex["all_pass"] = False

    merged = list(items.values())
    for item in merged:
        ex = item["execution"]
        ex["status"] = "executed" if ex["all_pass"] else "partial"
    return merged


def generate_report(team_results: list[dict], merged_plan: list[dict], total_ms: int) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    total_workers = sum(t["workers"] for t in team_results)
    total_pass = sum(t["passed"] for t in team_results)
    all_teams_pass = all(t["all_pass"] for t in team_results)

    lines = [
        "# Peerless Plan Execution Report",
        "",
        f"**Generated:** {now}  ",
        f"**Teams:** 4 (alpha, beta, gamma, delta)  ",
        f"**Workers:** {total_workers} (4 × 6)  ",
        f"**Passed:** {total_pass}/{total_workers}  ",
        f"**Duration:** {total_ms}ms  ",
        f"**Status:** {'🌟 ALL TEAMS PASS' if all_teams_pass else '🟡 PARTIAL'}  ",
        "",
        "## Team Summary",
        "",
        "| Team | Focus | Workers | Passed | Duration |",
        "|------|-------|---------|--------|----------|",
    ]
    focus = {"alpha": "P0 (WASM, self-host, codegen)", "beta": "Runtimes (GPU, CDX, IPFS)", "gamma": "Platform (peerless, knowledge, security)", "delta": "Docs, maintenance, ARC verify"}
    for t in team_results:
        lines.append(f"| {t['team']} | {focus.get(t['team'], '')} | {t['workers']} | {t['passed']}/{t['workers']} | {t['duration_ms']}ms |")

    lines.extend(["", "## Plan Item Execution", "", "| Plan ID | Theme | Status | Workers |", "|---------|-------|--------|---------|"])
    for item in merged_plan:
        ex = item.get("execution", {})
        status = "✅" if ex.get("all_pass") else "🟡"
        lines.append(f"| {item.get('plan_id')} | {item.get('theme')} | {status} {ex.get('status', 'pending')} | {ex.get('passed', 0)}/{ex.get('total', 0)} |")

    lines.extend(["", "## Worker Details", ""])
    for t in team_results:
        lines.append(f"### Team {t['team'].upper()}")
        lines.append("")
        for r in t["results"]:
            icon = "✅" if r["pass"] else "❌"
            lines.append(f"- {icon} `{r['worker_id']}` {r['label']} ({r['plan_id']}) — {r['duration_ms']}ms")
        lines.append("")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def run_execution() -> dict:
    plog = ProcessLogger(worker_id="plan_executor")
    start = time.perf_counter()
    plog.log("plan_execution", "start", "running", {"teams": 4, "workers": 24})

    team_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(execute_team, team, plog): team for team in TEAMS}
        for fut in as_completed(futures):
            team_results.append(fut.result())

    team_results.sort(key=lambda x: x["team"])
    merged_plan = merge_plan_execution(team_results)
    total_ms = int((time.perf_counter() - start) * 1000)

    total_workers = sum(t["workers"] for t in team_results)
    total_pass = sum(t["passed"] for t in team_results)
    plan_executed = sum(1 for p in merged_plan if p.get("execution", {}).get("all_pass"))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "teams": 4,
        "workers_per_team": WORKERS_PER_TEAM,
        "total_workers": total_workers,
        "workers_passed": total_pass,
        "all_pass": total_pass == total_workers,
        "plan_items": len(merged_plan),
        "plan_items_executed": plan_executed,
        "duration_ms": total_ms,
        "team_results": team_results,
        "merged_plan": merged_plan,
        "report": str(REPORT.relative_to(ROOT)),
    }

    EXEC_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    EXEC_MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Update plan manifest with execution status
    if PLAN_MANIFEST.exists():
        plan_data = json.loads(PLAN_MANIFEST.read_text(encoding="utf-8"))
        plan_data["execution"] = {
            "executed_at": summary["generated_at"],
            "all_pass": summary["all_pass"],
            "workers_passed": f"{total_pass}/{total_workers}",
            "plan_items_executed": plan_executed,
        }
        plan_data["plan"] = merged_plan
        PLAN_MANIFEST.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

    generate_report(team_results, merged_plan, total_ms)
    plog.log("plan_execution", "complete", "pass" if summary["all_pass"] else "partial", {"duration_ms": total_ms})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="4 teams × 6 workers execute Peerless plan")
    parser.add_argument("--teams", type=int, default=4)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.teams != 4 or args.workers != 6:
        print("This orchestrator is fixed at 4 teams × 6 workers", file=sys.stderr)
    summary = run_execution()
    print(json.dumps({
        "pass": summary["all_pass"],
        "teams": summary["teams"],
        "total_workers": summary["total_workers"],
        "workers_passed": summary["workers_passed"],
        "plan_items_executed": summary["plan_items_executed"],
        "duration_ms": summary["duration_ms"],
        "report": summary["report"],
        "manifest": str(EXEC_MANIFEST.relative_to(ROOT)),
    }, indent=2))
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
