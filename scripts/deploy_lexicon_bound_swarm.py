#!/usr/bin/env python3
"""
Deploy Lexicon-Bound Worker swarm — 4 teams × 6 workers (24 total).

Redeploys the same swarm structure with every action bound to the Lexicon.
Every worker, every user ticket, every deployment leaves a permanent trace.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lexicon_bound_worker import LexiconBoundWorker, save_tickets, UserTicket  # noqa: E402
from process_logger import ProcessLogger  # noqa: E402

MANIFEST = ROOT / "manifest" / "lexicon_bound_deployment.json"
REPORT = ROOT / "audit_reports/lexicon_bound_deployment_report.md"

TEAMS = ("alpha", "beta", "gamma", "delta")
WORKERS_PER_TEAM = 6
USER_ID = "frontier_cloud_agent"


def _verify_fr(path: str) -> list[str]:
    return [
        "python3", "-c",
        f"from pathlib import Path; p=Path('{path}'); "
        "assert p.exists() and p.stat().st_size > 20; print('PASS:', p)",
    ]
WORKER_TASKS: dict[str, list[dict]] = {
    "alpha": [
        {"id": "A1", "action": "wasm_build", "cmd": ["python3", "scripts/optimize_wasm_size.py"], "doc": "Lexicon-bound WASM size optimization"},
        {"id": "A2", "action": "wasm_manifest", "cmd": ["python3", "-c", "import json; print(json.load(open('manifest/wasm_size.json')))"], "doc": "Lexicon-bound WASM manifest read"},
        {"id": "A3", "action": "self_host_verify", "cmd": ["python3", "scripts/verify_self_hosting.py"], "doc": "Lexicon-bound self-hosting verification"},
        {"id": "A4", "action": "main_fr_parse", "cmd": ["cargo", "run", "--quiet", "--bin", "frontier", "--", "parse", "frontier/src/main.fr"], "doc": "Lexicon-bound main.fr parse"},
        {"id": "A5", "action": "wasm_codegen_tests", "cmd": ["cargo", "test", "--lib", "wasm_codegen::"], "doc": "Lexicon-bound wasm_codegen tests"},
        {"id": "A6", "action": "lexicon_core_verify", "cmd": _verify_fr("frontier/lexicon/core.fr"), "doc": "Lexicon-bound core.fr verified"},
    ],
    "beta": [
        {"id": "B1", "action": "gpu_runtime", "cmd": ["python3", "scripts/runtime_gpu.py"], "doc": "Lexicon-bound GPU runtime"},
        {"id": "B2", "action": "cdx_runtime", "cmd": ["python3", "scripts/runtime_cdx.py"], "doc": "Lexicon-bound CDX runtime"},
        {"id": "B3", "action": "ipfs_runtime", "cmd": ["python3", "scripts/runtime_ipfs.py"], "doc": "Lexicon-bound IPFS runtime"},
        {"id": "B4", "action": "tag_fr_verify", "cmd": _verify_fr("frontier/lexicon/tag.fr"), "doc": "Lexicon-bound tag.fr verified"},
        {"id": "B5", "action": "worker_fr_verify", "cmd": _verify_fr("frontier/worker/lexicon_bound.fr"), "doc": "Lexicon-bound worker.fr verified"},
        {"id": "B6", "action": "hard_gate_verify", "cmd": _verify_fr("frontier/lexicon/hard_gate.fr"), "doc": "Lexicon-bound hard_gate.fr verified"},
    ],
    "gamma": [
        {"id": "G1", "action": "close_peerless", "cmd": ["python3", "scripts/close_peerless_gaps.py"], "doc": "Lexicon-bound peerless gap closure"},
        {"id": "G2", "action": "sync_knowledge", "cmd": ["python3", "scripts/sync_knowledge_base.py"], "doc": "Lexicon-bound knowledge sync"},
        {"id": "G3", "action": "lexicon_ingest", "cmd": ["python3", "scripts/lexicon_ingest.py"], "doc": "Lexicon-bound ingest to hypercube"},
        {"id": "G4", "action": "spec_impl_bridge", "cmd": ["python3", "scripts/spec_impl_bridge.py"], "doc": "Lexicon-bound spec/impl bridge"},
        {"id": "G5", "action": "zk_tests", "cmd": ["cargo", "test", "--lib", "zk::"], "doc": "Lexicon-bound ZK security tests"},
        {"id": "G6", "action": "user_ticket_verify", "cmd": _verify_fr("frontier/lexicon/user_ticket.fr"), "doc": "Lexicon-bound user_ticket.fr verified"},
    ],
    "delta": [
        {"id": "D1", "action": "arc_status", "cmd": ["python3", "scripts/generate_arc_status.py"], "doc": "Lexicon-bound ARC status generation"},
        {"id": "D2", "action": "lib_tests", "cmd": ["cargo", "test", "--lib"], "doc": "Lexicon-bound lib tests"},
        {"id": "D3", "action": "lexicon_export", "cmd": ["python3", "scripts/lexicon_export.py"], "doc": "Lexicon-bound export for LLM training"},
        {"id": "D4", "action": "lexicon_index_check", "cmd": ["python3", "-c", "import json; d=json.load(open('manifest/lexicon_index.json')); print(d.get('entry_count',0))"], "doc": "Lexicon-bound index entry count check"},
        {"id": "D5", "action": "language_hardening", "cmd": ["python3", "scripts/verify_language_hardening.py"], "doc": "Lexicon-bound language hardening"},
        {"id": "D6", "action": "arc_verify", "cmd": ["python3", "build/arc_orchestrator.py", "--verify"], "doc": "Lexicon-bound full ARC verification"},
    ],
}


def run_worker(team: str, task: dict, ticket: UserTicket, plog: ProcessLogger) -> dict:
    worker_id = f"lexicon_{team}_{task['id']}"
    lbw = LexiconBoundWorker(worker_id=worker_id, user_id=USER_ID)
    result = lbw.execute_command(
        action=task["action"],
        cmd=task["cmd"],
        documentation=task["doc"],
        user_id=USER_ID,
    )
    ticket.add_action(result["lexicon_tag"])
    plog.log(
        task["action"],
        f"lexicon_bound_{team}",
        "pass" if result["pass"] else "fail",
        {"lexicon_tag": result["lexicon_tag"], "team": team, "worker": task["id"]},
    )
    return {
        "team": team,
        "worker_id": task["id"],
        "action": task["action"],
        "lexicon_tag": result["lexicon_tag"],
        "pass": result["pass"],
        "duration_ms": result["output"].get("duration_ms", 0),
    }


def execute_team(team: str, ticket: UserTicket, plog: ProcessLogger) -> dict:
    tasks = WORKER_TASKS[team]
    start = time.perf_counter()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS_PER_TEAM) as pool:
        futures = [pool.submit(run_worker, team, t, ticket, plog) for t in tasks]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda x: x["worker_id"])
    passed = sum(1 for r in results if r["pass"])
    return {
        "team": team,
        "workers": len(results),
        "passed": passed,
        "all_pass": passed == len(results),
        "lexicon_tags": [r["lexicon_tag"] for r in results],
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "results": results,
    }


def generate_report(summary: dict) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines = [
        "# Lexicon-Bound Worker Deployment Report",
        "",
        f"**Generated:** {now}  ",
        f"**ARC Verdict:** {'🌟 LEXICON-BOUND — ALL ACTIONS DOCUMENTED' if summary['all_pass'] else '🟡 PARTIAL'}  ",
        f"**Teams:** 4 × 6 workers = {summary['total_workers']}  ",
        f"**Lexicon entries:** {summary['lexicon_entries']}  ",
        f"**User ticket:** `{summary['ticket_id']}`  ",
        "",
        "## ARC Gates",
        "",
    ]
    for g in summary.get("arc_gates", []):
        icon = "✅" if g.get("pass") else "❌"
        lines.append(f"- {icon} **{g['gate']}**: {g.get('message', '')}")

    lines.extend(["", "## Team Results", "", "| Team | Passed | Lexicon Tags |", "|------|--------|--------------|"])
    for t in summary.get("team_results", []):
        lines.append(f"| {t['team']} | {t['passed']}/{t['workers']} | {len(t.get('lexicon_tags', []))} |")

    lines.extend([
        "",
        "## Protocol",
        "",
        "Every action carries a Lexicon Tag (`action_id`, `user_id` hashed, `worker_id`,",
        "`input_hash`, `output_hash`, `lexicon_entry`, `documentation`, `knowledge_delta`).",
        "",
        f"*Log: `docs/lexicon_log.fr` | Index: `manifest/lexicon_index.json`*",
    ])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def deploy() -> dict:
    plog = ProcessLogger(worker_id="lexicon_deploy")
    start = time.perf_counter()

    ticket = LexiconBoundWorker.create_user_ticket(USER_ID)
    plog.log("lexicon_deploy", "ticket_created", "pass", {"ticket_id": ticket.ticket_id})

    team_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(execute_team, team, ticket, plog): team for team in TEAMS}
        for fut in as_completed(futures):
            team_results.append(fut.result())
    team_results.sort(key=lambda x: x["team"])

    close = ticket.close()
    save_tickets([ticket])

    # Ingest + export
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "lexicon_ingest.py")], cwd=ROOT, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "lexicon_export.py")], cwd=ROOT, capture_output=True)

    # ARC gates
    arc_r = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_lexicon_bound.py")], cwd=ROOT, capture_output=True, text=True)
    arc_gates = []
    arc_manifest = ROOT / "manifest" / "lexicon_bound_arc.json"
    if arc_manifest.exists():
        arc_gates = json.loads(arc_manifest.read_text()).get("gates", [])

    index_path = ROOT / "manifest" / "lexicon_index.json"
    lexicon_count = 0
    if index_path.exists():
        lexicon_count = json.loads(index_path.read_text()).get("entry_count", 0)

    total_workers = sum(t["workers"] for t in team_results)
    total_pass = sum(t["passed"] for t in team_results)
    all_pass = total_pass == total_workers and arc_r.returncode == 0

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol": "lexicon_bound_worker",
        "teams": 4,
        "workers_per_team": 6,
        "total_workers": total_workers,
        "workers_passed": total_pass,
        "all_pass": all_pass,
        "lexicon_entries": lexicon_count,
        "ticket_id": ticket.ticket_id,
        "user_id_hash": ticket.to_dict()["user_id"],
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "team_results": team_results,
        "arc_gates": arc_gates,
        "arc_all_pass": arc_r.returncode == 0,
        "report": str(REPORT.relative_to(ROOT)),
    }
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generate_report(summary)
    plog.log("lexicon_deploy", "complete", "pass" if all_pass else "partial", {"entries": lexicon_count})
    return summary


def main() -> int:
    summary = deploy()
    print(json.dumps({
        "pass": summary["all_pass"],
        "workers": summary["total_workers"],
        "workers_passed": summary["workers_passed"],
        "lexicon_entries": summary["lexicon_entries"],
        "ticket_id": summary["ticket_id"],
        "arc_all_pass": summary["arc_all_pass"],
        "report": summary["report"],
    }, indent=2))
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
