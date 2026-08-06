#!/usr/bin/env python3
"""
Taylor Ops Team — tailored 7-worker / 3-group orchestrator.

Wires EVERY agent↔owner interaction script we have built into one command
so agents can run the full gambit (gates, GitHub, audit continuity) without
being prompted for each step.

Groups (3) / Workers (7):
  Group 1 TRUTH (3):
    W1 GateKeeper     → tracking.py gate
    W2 WasmVerifier   → verify_wasm_codegen + measure_wasm_size + cargo test --lib
    W3 AuditGuardian  → scrub_audit_sessions + validate_audit_log

  Group 2 GITHUB (2):
    W4 IssueMarshal   → gh issue list + dedupe_issues.py (report-only unless --apply)
    W5 PrScout        → gh pr list + CI workflow presence check

  Group 3 CONTINUITY (2):
    W6 KnowledgeScout → gather_ecosystem_knowledge --fast + sync_knowledge_base
    W7 ContinuityShadow → agent_shadow_worker run (README + heartbeat)

Modes:
  end-of-turn  — W3 + W7 (fast; agents call after every turn)
  daily        — all 7 workers, groups sequential, workers parallel within group
  full         — daily + repo snapshot gather + process_logger self-test

Usage:
  python3 scripts/taylor_ops_team.py run
  python3 scripts/taylor_ops_team.py run --mode end-of-turn
  python3 scripts/taylor_ops_team.py run --mode daily
  python3 scripts/taylor_ops_team.py run --mode full --apply
  python3 scripts/taylor_ops_team.py inventory
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
from typing import Any

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest" / "taylor_ops_team.json"
REPORT = REPO / "audit_reports" / "taylor_ops_team_report.md"
INVENTORY = REPO / "manifest" / "interaction_script_inventory.json"
LOGGER = REPO / "scripts" / "agent_audit_logger.py"

# ---------------------------------------------------------------------------
# Team roster — 7 workers in 3 groups
# ---------------------------------------------------------------------------

WORKERS: dict[str, dict[str, Any]] = {
    "W1_GateKeeper": {
        "group": 1,
        "name": "GateKeeper",
        "role": "Blueprint tracking gate",
        "scripts": ["scripts/tracking.py"],
        "commands": [
            [sys.executable, "scripts/tracking.py", "gate"],
        ],
        "allow_nonzero": True,  # gate FAIL is informative, not a crash
    },
    "W2_WasmVerifier": {
        "group": 1,
        "name": "WasmVerifier",
        "role": "WASM size + unit tests (+ wasmtime verifier if present)",
        "scripts": [
            "scripts/measure_wasm_size.py",
            "scripts/optimize_wasm_size.py",
        ],
        "commands": [
            [sys.executable, "scripts/measure_wasm_size.py"],
            ["cargo", "test", "--lib", "--quiet"],
        ],
        "optional_commands": [
            [sys.executable, "scripts/verify_wasm_codegen.py"],
            [sys.executable, "scripts/optimize_wasm_size.py"],
        ],
        "allow_nonzero": False,
    },
    "W3_AuditGuardian": {
        "group": 1,
        "name": "AuditGuardian",
        "role": "PII scrub + schema validate",
        "scripts": [
            "scripts/scrub_audit_sessions.py",
            "scripts/validate_audit_log.py",
        ],
        "commands": [
            [sys.executable, "scripts/scrub_audit_sessions.py"],
            [sys.executable, "scripts/validate_audit_log.py", "--strict-hash"],
        ],
        "allow_nonzero": False,
    },
    "W4_IssueMarshal": {
        "group": 2,
        "name": "IssueMarshal",
        "role": "Open issues inventory + dedupe",
        "scripts": ["scripts/dedupe_issues.py"],
        "commands": [
            ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels"],
        ],
        "apply_commands": [
            [sys.executable, "scripts/dedupe_issues.py"],
        ],
        "allow_nonzero": False,
    },
    "W5_PrScout": {
        "group": 2,
        "name": "PrScout",
        "role": "Open PRs + CI workflow presence",
        "scripts": ["scripts/swarm_resolve_prs.py", ".github/workflows/blueprint-gate.yml"],
        "commands": [
            ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,isDraft"],
        ],
        "allow_nonzero": False,
    },
    "W6_KnowledgeScout": {
        "group": 3,
        "name": "KnowledgeScout",
        "role": "Ecosystem gather + knowledge sync",
        "scripts": [
            "scripts/gather_ecosystem_knowledge.py",
            "scripts/sync_knowledge_base.py",
        ],
        "commands": [
            [sys.executable, "scripts/gather_ecosystem_knowledge.py", "--fast"],
            [sys.executable, "scripts/sync_knowledge_base.py"],
        ],
        "allow_nonzero": True,
    },
    "W7_ContinuityShadow": {
        "group": 3,
        "name": "ContinuityShadow",
        "role": "Shadow worker heartbeat + README live status",
        "scripts": [
            "scripts/agent_shadow_worker.py",
            "scripts/update_audit_readme.py",
        ],
        "commands": [
            [sys.executable, "scripts/agent_shadow_worker.py", "run"],
        ],
        "allow_nonzero": False,
    },
}

GROUPS: dict[int, dict[str, Any]] = {
    1: {
        "name": "TRUTH",
        "mission": "Blueprint gates, WASM truth, audit integrity",
        "workers": ["W1_GateKeeper", "W2_WasmVerifier", "W3_AuditGuardian"],
    },
    2: {
        "name": "GITHUB",
        "mission": "Issues, PRs, Actions — the whole gambit",
        "workers": ["W4_IssueMarshal", "W5_PrScout"],
    },
    3: {
        "name": "CONTINUITY",
        "mission": "Ecosystem knowledge + README/shadow continuity",
        "workers": ["W6_KnowledgeScout", "W7_ContinuityShadow"],
    },
}

MODES: dict[str, list[str]] = {
    "end-of-turn": ["W3_AuditGuardian", "W7_ContinuityShadow"],
    "daily": list(WORKERS.keys()),
    "full": list(WORKERS.keys()),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def audit_log(action: str, why: str, outputs: dict | None = None, verified: bool = True) -> None:
    if not LOGGER.exists():
        return
    cmd = [
        sys.executable,
        str(LOGGER),
        "record",
        "--category",
        "pipeline",
        "--action",
        action,
        "--why",
        why,
        "--script",
        "scripts/taylor_ops_team.py",
        "--outputs",
        json.dumps(outputs or {}, default=str),
    ]
    if verified:
        cmd.append("--verified")
    subprocess.run(cmd, cwd=REPO, capture_output=True)


def run_cmd(cmd: list[str], timeout: int = 300) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
        return {
            "command": " ".join(cmd),
            "exit_code": r.returncode,
            "pass": r.returncode == 0,
            "duration_s": round(time.perf_counter() - start, 3),
            "stdout_tail": (r.stdout or "")[-1500:],
            "stderr_tail": (r.stderr or "")[-800:],
        }
    except FileNotFoundError as e:
        return {
            "command": " ".join(cmd),
            "exit_code": 127,
            "pass": False,
            "duration_s": round(time.perf_counter() - start, 3),
            "stdout_tail": "",
            "stderr_tail": str(e),
            "missing": True,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "exit_code": 124,
            "pass": False,
            "duration_s": timeout,
            "stdout_tail": "",
            "stderr_tail": "timeout",
        }


def run_worker(wid: str, *, apply: bool = False) -> dict[str, Any]:
    spec = WORKERS[wid]
    result: dict[str, Any] = {
        "id": wid,
        "name": spec["name"],
        "group": spec["group"],
        "role": spec["role"],
        "scripts": spec["scripts"],
        "steps": [],
        "ok": True,
        "started_at": utc_now(),
    }

    cmds = list(spec.get("commands", []))
    if apply and spec.get("apply_commands"):
        cmds.extend(spec["apply_commands"])

    for cmd in cmds:
        # Skip optional scripts that do not exist
        if cmd[0] == sys.executable and len(cmd) > 1:
            script_path = REPO / cmd[1]
            if not script_path.exists():
                result["steps"].append(
                    {
                        "command": " ".join(cmd),
                        "pass": False,
                        "skipped": True,
                        "reason": f"script missing: {cmd[1]}",
                    }
                )
                # optional missing scripts do not fail the worker unless required
                if cmd in spec.get("optional_commands", []):
                    continue
                # required missing → fail
                if "verify_wasm_codegen" in cmd[1]:
                    continue  # optional until present
                result["ok"] = False
                continue

        step = run_cmd(cmd)
        result["steps"].append(step)
        if not step["pass"] and not spec.get("allow_nonzero", False):
            result["ok"] = False
        if not step["pass"] and spec.get("allow_nonzero"):
            step["informational_fail"] = True

    for cmd in spec.get("optional_commands", []):
        if cmd[0] == sys.executable and not (REPO / cmd[1]).exists():
            continue
        step = run_cmd(cmd)
        step["optional"] = True
        result["steps"].append(step)

    # Extra checks for PrScout: CI workflow exists
    if wid == "W5_PrScout":
        wf = REPO / ".github" / "workflows" / "blueprint-gate.yml"
        result["steps"].append(
            {
                "command": "check .github/workflows/blueprint-gate.yml",
                "pass": wf.exists(),
                "exit_code": 0 if wf.exists() else 1,
                "duration_s": 0,
                "stdout_tail": "present" if wf.exists() else "MISSING",
                "stderr_tail": "",
            }
        )
        if not wf.exists():
            result["ok"] = False

    result["finished_at"] = utc_now()
    return result


def run_group(gid: int, workers: list[str], *, apply: bool, parallel: bool) -> dict[str, Any]:
    meta = GROUPS[gid]
    group_result: dict[str, Any] = {
        "group": gid,
        "name": meta["name"],
        "mission": meta["mission"],
        "workers": [],
        "ok": True,
        "started_at": utc_now(),
    }

    active = [w for w in meta["workers"] if w in workers]
    if not active:
        group_result["skipped"] = True
        group_result["finished_at"] = utc_now()
        return group_result

    if parallel and len(active) > 1:
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            futs = {pool.submit(run_worker, w, apply=apply): w for w in active}
            for fut in as_completed(futs):
                wr = fut.result()
                group_result["workers"].append(wr)
                if not wr["ok"]:
                    group_result["ok"] = False
    else:
        for w in active:
            wr = run_worker(w, apply=apply)
            group_result["workers"].append(wr)
            if not wr["ok"]:
                group_result["ok"] = False

    # Keep worker order stable
    order = {w: i for i, w in enumerate(active)}
    group_result["workers"].sort(key=lambda x: order.get(x["id"], 99))
    group_result["finished_at"] = utc_now()
    return group_result


def write_report(run: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Taylor Ops Team Report",
        f"",
        f"**Run ID:** `{run['run_id']}`  ",
        f"**Mode:** `{run['mode']}`  ",
        f"**Started:** {run['started_at']}  ",
        f"**Finished:** {run['finished_at']}  ",
        f"**Overall:** {'PASS' if run['ok'] else 'PARTIAL / FAIL'}  ",
        f"",
        f"## Team roster (7 workers → 3 groups)",
        f"",
        f"| Group | Name | Workers |",
        f"|-------|------|---------|",
        f"| 1 | TRUTH | GateKeeper, WasmVerifier, AuditGuardian |",
        f"| 2 | GITHUB | IssueMarshal, PrScout |",
        f"| 3 | CONTINUITY | KnowledgeScout, ContinuityShadow |",
        f"",
    ]

    for g in run["groups"]:
        status = "PASS" if g.get("ok") else ("SKIP" if g.get("skipped") else "FAIL")
        lines.append(f"## Group {g['group']}: {g['name']} — {status}")
        lines.append(f"_{g['mission']}_")
        lines.append("")
        for w in g.get("workers", []):
            wstatus = "PASS" if w["ok"] else "FAIL"
            lines.append(f"### {w['id']} {w['name']} — {wstatus}")
            lines.append(f"Role: {w['role']}")
            lines.append("")
            lines.append("| Step | Exit | Duration |")
            lines.append("|------|------|----------|")
            for s in w["steps"]:
                cmd = s.get("command", "")[:80]
                lines.append(
                    f"| `{cmd}` | {s.get('exit_code')} | {s.get('duration_s', '?')}s |"
                )
            lines.append("")

    lines.append("## Confirmation")
    lines.append("")
    if run["ok"]:
        lines.append("**DONE.** All scheduled workers completed within policy.")
    else:
        lines.append("**DONE WITH FAILURES.** See FAIL workers above — agents must remediate.")
    lines.append("")
    lines.append(f"Inventory: `{INVENTORY.relative_to(REPO)}`")
    lines.append(f"Manifest: `{MANIFEST.relative_to(REPO)}`")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")


def cmd_inventory(_: argparse.Namespace) -> int:
    if INVENTORY.exists():
        data = json.loads(INVENTORY.read_text(encoding="utf-8"))
        total = sum(len(v) for v in data.get("categories", {}).values())
        print(json.dumps({"scripts_catalogued": total, "categories": {k: len(v) for k, v in data["categories"].items()}, "path": str(INVENTORY.relative_to(REPO))}, indent=2))
        return 0
    print("Inventory missing", file=sys.stderr)
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    mode = args.mode
    workers = list(MODES[mode])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    audit_log(
        "taylor_ops_team_start",
        f"Owner requested tailored 7/3 ops team — mode={mode}",
        {"mode": mode, "workers": workers, "apply": args.apply},
    )

    run: dict[str, Any] = {
        "run_id": run_id,
        "mode": mode,
        "apply": args.apply,
        "started_at": utc_now(),
        "workers_scheduled": workers,
        "groups": [],
        "ok": True,
    }

    # Groups sequential (TRUTH → GITHUB → CONTINUITY); workers parallel within group
    for gid in (1, 2, 3):
        group_workers = [w for w in GROUPS[gid]["workers"] if w in workers]
        if not group_workers:
            continue
        gr = run_group(gid, workers, apply=args.apply, parallel=not args.sequential)
        run["groups"].append(gr)
        if not gr.get("skipped") and not gr["ok"]:
            run["ok"] = False

    # Full mode: also refresh repo snapshot
    if mode == "full":
        snap = run_cmd([sys.executable, "scripts/agent_shadow_worker.py", "run", "--snapshot", "--no-readme"], timeout=600)
        run["full_snapshot"] = snap
        if not snap["pass"]:
            run["ok"] = False

    run["finished_at"] = utc_now()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(run, indent=2, default=str), encoding="utf-8")
    write_report(run)

    audit_log(
        "taylor_ops_team_complete",
        "Taylor Ops Team finished — confirmation written",
        {
            "run_id": run_id,
            "ok": run["ok"],
            "report": str(REPORT.relative_to(REPO)),
        },
        verified=True,
    )

    # Human confirmation line
    print(json.dumps({
        "done": True,
        "ok": run["ok"],
        "run_id": run_id,
        "mode": mode,
        "groups": [
            {
                "group": g["group"],
                "name": g["name"],
                "ok": g.get("ok"),
                "workers": [
                    {"id": w["id"], "name": w["name"], "ok": w["ok"]}
                    for w in g.get("workers", [])
                ],
            }
            for g in run["groups"]
        ],
        "report": str(REPORT.relative_to(REPO)),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "confirmation": "DONE" if run["ok"] else "DONE_WITH_FAILURES",
    }, indent=2))
    return 0 if run["ok"] else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Ops Team — 7 workers / 3 groups")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run the ops team")
    r.add_argument(
        "--mode",
        choices=list(MODES.keys()),
        default="daily",
        help="end-of-turn | daily | full (default: daily)",
    )
    r.add_argument("--apply", action="store_true", help="allow mutating GitHub actions (dedupe)")
    r.add_argument("--sequential", action="store_true", help="disable within-group parallelism")
    r.set_defaults(func=cmd_run)

    inv = sub.add_parser("inventory", help="Show interaction script inventory")
    inv.set_defaults(func=cmd_inventory)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
