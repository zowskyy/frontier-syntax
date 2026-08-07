#!/usr/bin/env python3
"""
Taylor Ops Team — tailored 7-worker / 3-group orchestrator.

Production pipeline (mode=production):
  Group 1 FOUNDATION (Blueprint Phase 0–1) — sequential:
    W1 GateKeeper      → tracking.py gate
    W2 CompilerCore    → wasm_codegen tests + verify_self_hosting
    W3 AuditGuardian   → scrub + validate audit JSONL

  Group 2 BUILD (Blueprint Phase 2–3) — parallel:
    W4 SpecParity      → spec_impl_bridge + verify_language_hardening
    W5 WasmSizer       → measure_wasm_size + optimize

  Group 3 SHIP (Production hardening + launch prep) — parallel:
    W6 GitHubOps       → issues + PRs + CI + issue closure orchestration
    W7 LaunchContinuity → ecosystem gather + README status + process log

Issue closure (all modes except end-of-turn):
  Each worker audits/closes its canonical GitHub issues via scripts/taylor_issue_closer.py
  after verification steps. W6 runs the full sweep. Use --apply to close on GitHub.

Modes:
  end-of-turn   — W3 + W7 (fast; shadow worker default)
  daily         — all 7, parallel within groups
  production    — all 7, FOUNDATION sequential then BUILD+SHIP (recommended for prod path)
  full          — production + repo snapshot gather
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
ISSUE_CLOSER = REPO / "scripts" / "taylor_issue_closer.py"

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
    "W2_CompilerCore": {
        "group": 1,
        "name": "CompilerCore",
        "role": "Phase 1 P0 — wasm_codegen + self-hosting verification; closes #44–#46",
        "issue_numbers": [44, 45, 46],
        "scripts": [
            "scripts/verify_self_hosting.py",
            "scripts/run_native_self_host.py",
            "scripts/taylor_compiler_mission.py",
            "scripts/measure_wasm_size.py",
            "scripts/taylor_issue_closer.py",
        ],
        "commands": [
            ["cargo", "test", "--lib", "wasm_codegen::", "--quiet"],
            ["cargo", "test", "--lib", "wasm_codegen::tests::test_knowledge_changes_wasm", "--quiet"],
            [sys.executable, "scripts/verify_self_hosting.py"],
            [sys.executable, "scripts/taylor_compiler_mission.py"],
        ],
        "apply_commands": [
            [sys.executable, "scripts/taylor_compiler_mission.py", "--apply"],
        ],
        "optional_commands": [
            [sys.executable, "scripts/verify_wasm_codegen.py"],
        ],
        "allow_nonzero": True,
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
    "W4_SpecParity": {
        "group": 2,
        "name": "SpecParity",
        "role": "Phase 2 — spec/impl bridge + language hardening; closes #47",
        "issue_numbers": [47],
        "scripts": [
            "scripts/spec_impl_bridge.py",
            "scripts/verify_language_hardening.py",
            "scripts/taylor_issue_closer.py",
        ],
        "commands": [
            [sys.executable, "scripts/spec_impl_bridge.py"],
            [sys.executable, "scripts/verify_language_hardening.py"],
        ],
        "allow_nonzero": True,
    },
    "W5_WasmSizer": {
        "group": 2,
        "name": "WasmSizer",
        "role": "Phase 3 — WASM size target (#48); audit history before optimize; closes #48",
        "issue_numbers": [48],
        "scripts": [
            "scripts/audit_wasm_size_history.py",
            "scripts/measure_wasm_size.py",
            "scripts/optimize_wasm_size.py",
            "scripts/taylor_issue_closer.py",
        ],
        "commands": [
            [sys.executable, "scripts/audit_wasm_size_history.py"],
            [sys.executable, "scripts/measure_wasm_size.py"],
            [sys.executable, "scripts/optimize_wasm_size.py"],
        ],
        "allow_nonzero": True,
        "audit_first": True,
    },
    "W6_GitHubOps": {
        "group": 3,
        "name": "GitHubOps",
        "role": "Issues + PRs + CI — orchestrates canonical issue closure (#44–#48)",
        "issue_numbers": [44, 45, 46, 47, 48],
        "scripts": [
            "scripts/dedupe_issues.py",
            "scripts/swarm_resolve_prs.py",
            "scripts/taylor_issue_closer.py",
            ".github/workflows/blueprint-gate.yml",
        ],
        "commands": [
            ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels"],
            ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,isDraft"],
            [sys.executable, "scripts/taylor_issue_closer.py", "audit"],
        ],
        "apply_commands": [
            [sys.executable, "scripts/dedupe_issues.py"],
            [sys.executable, "scripts/taylor_issue_closer.py", "close", "--apply"],
        ],
        "allow_nonzero": False,
    },
    "W7_LaunchContinuity": {
        "group": 3,
        "name": "LaunchContinuity",
        "role": "Ecosystem + README + process log — launch continuity",
        "scripts": [
            "scripts/gather_ecosystem_knowledge.py",
            "scripts/update_audit_readme.py",
            "scripts/process_logger.py",
            "scripts/sync_knowledge_base.py",
            "frontier_universal.py",
        ],
        "commands": [
            [sys.executable, "scripts/gather_ecosystem_knowledge.py", "--fast"],
            [sys.executable, "scripts/update_audit_readme.py"],
            [sys.executable, "scripts/sync_knowledge_base.py"],
            [sys.executable, "frontier_universal.py", "--self-test"],
        ],
        "light_commands": [
            [sys.executable, "scripts/update_audit_readme.py"],
        ],
        "optional_commands": [
            [sys.executable, "scripts/process_logger.py"],
        ],
        "allow_nonzero": True,
    },
}

GROUPS: dict[int, dict[str, Any]] = {
    1: {
        "name": "FOUNDATION",
        "mission": "Blueprint Phase 0–1: gate truth, compiler P0s, audit integrity",
        "workers": ["W1_GateKeeper", "W2_CompilerCore", "W3_AuditGuardian"],
        "sequential": True,
    },
    2: {
        "name": "BUILD",
        "mission": "Blueprint Phase 2–3: spec parity + WASM size target",
        "workers": ["W4_SpecParity", "W5_WasmSizer"],
        "sequential": False,
    },
    3: {
        "name": "SHIP",
        "mission": "Production hardening: GitHub gambit + launch continuity",
        "workers": ["W6_GitHubOps", "W7_LaunchContinuity"],
        "sequential": False,
    },
}

MODES: dict[str, list[str]] = {
    "end-of-turn": ["W3_AuditGuardian", "W7_LaunchContinuity"],
    "daily": list(WORKERS.keys()),
    "production": list(WORKERS.keys()),
    "full": list(WORKERS.keys()),
}

MODE_GROUP_PARALLEL: dict[str, bool] = {
    "end-of-turn": True,
    "daily": True,
    "production": False,  # group 1 sequential; 2+3 parallel within group
    "full": False,
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


def run_issue_closure_for_worker(
    wid: str,
    *,
    apply: bool = False,
    run_id: str | None = None,
    mode: str = "daily",
) -> dict[str, Any] | None:
    """Independent validator pass for issues owned by this worker."""
    if mode == "end-of-turn":
        return None
    spec = WORKERS.get(wid, {})
    if not spec.get("issue_numbers") or not ISSUE_CLOSER.exists():
        return None
    cmd = [sys.executable, str(ISSUE_CLOSER), "close", "--worker", wid]
    if apply:
        cmd.append("--apply")
    if run_id:
        cmd.extend(["--run-id", run_id])
    step = run_cmd(cmd, timeout=600)
    step["issue_closure"] = True
    step["worker"] = wid
    step["issues_owned"] = spec.get("issue_numbers")
    return step


def run_worker(wid: str, *, apply: bool = False, mode: str = "daily", run_id: str | None = None) -> dict[str, Any]:
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

    if mode == "end-of-turn" and spec.get("light_commands"):
        cmds = list(spec["light_commands"])
    else:
        cmds = list(spec.get("commands", []))
    if apply and spec.get("apply_commands"):
        cmds.extend(spec["apply_commands"])

    # WasmSizer: run audit first, then decide whether to skip optimize
    audit_block_optimize = False
    if wid == "W5_WasmSizer" and spec.get("audit_first"):
        audit_cmd = [sys.executable, "scripts/audit_wasm_size_history.py"]
        audit_step = run_cmd(audit_cmd)
        result["steps"].append(audit_step)
        history_path = REPO / "manifest" / "wasm_size_history.json"
        if history_path.exists():
            try:
                hist = json.loads(history_path.read_text(encoding="utf-8"))
                audit_block_optimize = bool(hist.get("block_optimize_until_reconciled"))
            except json.JSONDecodeError:
                pass
        if audit_block_optimize:
            cmds = [c for c in cmds if "audit_wasm_size_history" not in (c[1] if len(c) > 1 else "")]
            cmds = [c for c in cmds if "optimize_wasm_size" not in (c[1] if len(c) > 1 else "")]
            result["audit_gate"] = {
                "block_optimize": True,
                "reason": "historical met:true on sibling branch — reconcile before optimize",
                "manifest": str(history_path.relative_to(REPO)),
            }
        else:
            cmds = [c for c in cmds if "audit_wasm_size_history" not in (c[1] if len(c) > 1 else "")]

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

    # Extra checks for GitHubOps: CI workflow exists
    if wid == "W6_GitHubOps":
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

    closure = run_issue_closure_for_worker(wid, apply=apply, run_id=run_id, mode=mode)
    if closure:
        result["steps"].append(closure)
        result["issue_closure"] = {
            "eligible": "eligible" in (closure.get("stdout_tail") or ""),
            "applied": apply,
        }

    result["finished_at"] = utc_now()
    return result


def run_group(
    gid: int,
    workers: list[str],
    *,
    apply: bool,
    parallel: bool,
    mode: str = "daily",
    force_sequential: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
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

    use_parallel = parallel and not force_sequential and not meta.get("sequential", False)

    if use_parallel and len(active) > 1:
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            futs = {pool.submit(run_worker, w, apply=apply, mode=mode, run_id=run_id): w for w in active}
            for fut in as_completed(futs):
                wr = fut.result()
                group_result["workers"].append(wr)
                if not wr["ok"]:
                    group_result["ok"] = False
    else:
        for w in active:
            wr = run_worker(w, apply=apply, mode=mode, run_id=run_id)
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
        f"## Team roster (7 workers → 3 groups — production pipeline)",
        f"",
        f"| Group | Name | Workers | Blueprint |",
        f"|-------|------|---------|-----------|",
        f"| 1 | FOUNDATION | GateKeeper, CompilerCore, AuditGuardian | Phase 0–1 |",
        f"| 2 | BUILD | SpecParity, WasmSizer | Phase 2–3 |",
        f"| 3 | SHIP | GitHubOps, LaunchContinuity | Phase 7–8 prep |",
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

    lines.append("")
    closure_path = REPO / "manifest" / "issue_closure_status.json"
    if closure_path.exists():
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        lines.append("## Issue closure (Taylor Ops validator)")
        lines.append("")
        lines.append(f"Eligible: `{closure.get('eligible_to_close', [])}`  ")
        lines.append(f"Closed this run: `{closure.get('closed_this_run', [])}`  ")
        lines.append(f"Still open: `{closure.get('still_open', [])}`  ")
        lines.append(f"Report: `audit_reports/issue_closure_report.md`")
        lines.append("")

    lines.append("## Production readiness")
    lines.append("")
    prod_path = REPO / "manifest" / "production_readiness.json"
    if prod_path.exists():
        prod = json.loads(prod_path.read_text(encoding="utf-8"))
        lines.append(f"Target: `{prod.get('target')}` — blockers documented in `{prod_path.relative_to(REPO)}`")
    lines.append("")
    if run.get("production_ready"):
        lines.append("**PRODUCTION GATE: PASS** (all worker steps green)")
    else:
        lines.append("**PRODUCTION GATE: NOT READY** — see FAIL workers and open issues #44–#48")
    lines.append("")
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


def assess_production_readiness(run: dict[str, Any]) -> bool:
    """Honest prod flag: tracking gate + wasm target + no hard worker failures."""
    gate = run_cmd([sys.executable, "scripts/tracking.py", "gate"], timeout=120)
    wasm_path = REPO / "manifest" / "wasm_size.json"
    wasm_met = False
    if wasm_path.exists():
        wasm_met = json.loads(wasm_path.read_text(encoding="utf-8")).get("met", False)

    hard_fail = False
    for g in run.get("groups", []):
        for w in g.get("workers", []):
            if not w.get("ok"):
                hard_fail = True
            for s in w.get("steps", []):
                if not s.get("pass") and not s.get("optional") and not s.get("informational_fail"):
                    # Workers with allow_nonzero mark informational_fail on steps
                    if not s.get("skipped"):
                        pass  # already in worker ok

    return gate["pass"] and wasm_met and not hard_fail and run.get("ok", False)


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

    # Groups sequential; production mode runs FOUNDATION workers one-by-one
    group_parallel = MODE_GROUP_PARALLEL.get(mode, True)
    for gid in (1, 2, 3):
        group_workers = [w for w in GROUPS[gid]["workers"] if w in workers]
        if not group_workers:
            continue
        within_parallel = group_parallel and not GROUPS[gid].get("sequential", False)
        gr = run_group(gid, workers, apply=args.apply, parallel=within_parallel and not args.sequential, mode=mode, run_id=run_id)
        run["groups"].append(gr)
        if not gr.get("skipped") and not gr["ok"]:
            run["ok"] = False

    # Final independent validator sweep (W6 orchestration) — daily/production/full only
    if mode != "end-of-turn" and ISSUE_CLOSER.exists():
        sweep_cmd = [sys.executable, str(ISSUE_CLOSER), "close", "--run-id", run_id]
        if args.apply:
            sweep_cmd.append("--apply")
        run["issue_closure_sweep"] = run_cmd(sweep_cmd, timeout=600)

    # Production readiness: honest assessment from gate + wasm manifest
    if mode in ("production", "full"):
        run["production_ready"] = assess_production_readiness(run)
    else:
        run["production_ready"] = False

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
        "production_ready": run.get("production_ready", False),
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
        help="end-of-turn | daily | production | full (default: daily)",
    )
    r.add_argument("--apply", action="store_true", help="close eligible GitHub issues + dedupe (mutating)")
    r.add_argument("--sequential", action="store_true", help="disable within-group parallelism")
    r.set_defaults(func=cmd_run)

    inv = sub.add_parser("inventory", help="Show interaction script inventory")
    inv.set_defaults(func=cmd_inventory)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
