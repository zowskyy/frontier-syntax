#!/usr/bin/env python3
"""
Taylor Compiler 30 — 3 teams × 10 workers to finish compiler → RELEASE_READY.

Team 1 FOUNDATION (T1-1..T1-10): env bootstrap, self-host, Phase 5 gate
Team 2 BUILD      (T2-1..T2-10): Phase 4 innovations + Phase 6 corpus
Team 3 SHIP       (T3-1..T3-10): Phases 7–8, tracking, GA, ops continuity

Usage:
  python scripts/taylor_compiler_30.py run [--apply] [--skip-env]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "taylor_compiler_30.json"
REPORT = ROOT / "audit_reports" / "taylor_compiler_30_report.md"
GA_STATUS = ROOT / "manifest" / "ga_status.json"

INNOVATIONS = [
    ("T2-2", "grammar::", "src/grammar/mutator.rs"),
    ("T2-3", "compiler::proof_generator::", "src/compiler/proof_generator.rs"),
    ("T2-4", "pq_signatures::", "src/pq_signatures.rs"),
    ("T2-5", "zk::verifier::", "src/zk/verifier.rs"),
    ("T2-6", "ipfs::resolver::", "src/ipfs/resolver.rs"),
    ("T2-7", "neural::completion::", "src/neural/completion.rs"),
    ("T2-8", "packages::registry::", "src/packages/registry.rs"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], timeout: int = 1800) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        tail = (r.stdout + r.stderr)[-800:]
        code = r.returncode
    except FileNotFoundError as exc:
        ok = False
        tail = str(exc)
        code = -1
    except subprocess.TimeoutExpired:
        ok = False
        tail = "timeout"
        code = -1
    return {
        "command": " ".join(cmd),
        "pass": ok,
        "exit_code": code,
        "duration_s": round(time.perf_counter() - start, 2),
        "output_tail": tail,
    }


def worker_result(wid: str, name: str, team: str, step: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "id": wid,
        "name": name,
        "team": team,
        "pass": step.get("pass", False),
        "step": step,
        **extra,
    }


# ---------------------------------------------------------------------------
# Team 1 — FOUNDATION
# ---------------------------------------------------------------------------

def t1_1_env_bootstrap() -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    has_target = False
    r = subprocess.run(["rustup", "target", "list", "--installed"], capture_output=True, text=True)
    if r.returncode == 0:
        has_target = "wasm32-unknown-unknown" in r.stdout
    if not has_target:
        steps.append(run_cmd(["rustup", "target", "add", "wasm32-unknown-unknown"]))
        has_target = steps[-1]["pass"]
    wasmtime_ok = shutil.which("wasmtime") is not None
    return worker_result(
        "T1-1", "EnvBootstrap", "FOUNDATION",
        {"pass": has_target and wasmtime_ok, "wasm32_target": has_target, "wasmtime": wasmtime_ok},
        steps=steps,
    )


def t1_2_wasm_codegen_tests() -> dict[str, Any]:
    return worker_result("T1-2", "WasmCodegenTests", "FOUNDATION", run_cmd(["cargo", "test", "--lib", "wasm_codegen::", "--quiet"]))


def t1_3_native_probe() -> dict[str, Any]:
    return worker_result("T1-3", "NativeProbe", "FOUNDATION", run_cmd([sys.executable, "scripts/run_native_self_host.py"]))


def t1_4_self_host_verify() -> dict[str, Any]:
    return worker_result("T1-4", "SelfHostVerify", "FOUNDATION", run_cmd([sys.executable, "scripts/verify_self_hosting.py", "--native"]))


def t1_5_compiler_mission(apply: bool) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/taylor_compiler_mission.py"]
    if apply:
        cmd.append("--apply")
    return worker_result("T1-5", "CompilerMission", "FOUNDATION", run_cmd(cmd))


def t1_6_p5_diagnose() -> dict[str, Any]:
    main = ROOT / "frontier" / "src" / "main.fr"
    blockers = []
    if main.exists():
        text = main.read_text(encoding="utf-8")
        blockers = [b for b in ("version:", "import ") if b in text]
    return worker_result("T1-6", "P5Diagnose", "FOUNDATION", {"pass": main.exists() and not blockers, "blockers": blockers})


def t1_7_p5_preflight() -> dict[str, Any]:
    main = ROOT / "frontier" / "src" / "main.fr"
    text = main.read_text(encoding="utf-8") if main.exists() else ""
    ok = "fn compile(" in text and "fn main()" in text
    return worker_result("T1-7", "P5Preflight", "FOUNDATION", {"pass": ok})


def t1_8_p5_verify() -> dict[str, Any]:
    step = run_cmd([sys.executable, "scripts/verify_main_fr_native.py"])
    manifest_pass = False
    mf = ROOT / "manifest" / "main_fr_native.json"
    if mf.exists():
        try:
            manifest_pass = bool(json.loads(mf.read_text(encoding="utf-8")).get("pass"))
        except json.JSONDecodeError:
            pass
    return worker_result("T1-8", "P5Verify", "FOUNDATION", {"pass": step["pass"] and manifest_pass, "verify": step})


def t1_9_p5_mission(apply: bool) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/taylor_phase5_mission.py"]
    if apply:
        cmd.append("--apply")
    return worker_result("T1-9", "P5Mission", "FOUNDATION", run_cmd(cmd))


def t1_10_issue_close(apply: bool) -> dict[str, Any]:
    if not apply:
        return worker_result("T1-10", "IssueClose", "FOUNDATION", {"pass": True, "skipped": True})
    return worker_result(
        "T1-10", "IssueClose", "FOUNDATION",
        run_cmd([sys.executable, "scripts/taylor_issue_closer.py", "close", "--worker", "W2_CompilerCore", "--apply"]),
    )


# ---------------------------------------------------------------------------
# Team 2 — BUILD
# ---------------------------------------------------------------------------

def t2_1_innovations_gate() -> dict[str, Any]:
    return worker_result("T2-1", "InnovationsGate", "BUILD", run_cmd([sys.executable, "scripts/verify_innovations.py"]))


def t2_innovation_worker(wid: str, module: str, path: str) -> dict[str, Any]:
    src = ROOT / path
    if not src.exists():
        return worker_result(wid, f"Innovation_{module.rstrip(':')}", "BUILD", {"pass": False, "reason": "missing source"})
    return worker_result(wid, f"Innovation_{module.rstrip(':')}", "BUILD", run_cmd(["cargo", "test", "--lib", module, "--quiet"]))


def t2_9_p6_mission(apply: bool) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/taylor_phase6_mission.py"]
    if apply:
        cmd.append("--apply")
    return worker_result("T2-9", "P6Mission", "BUILD", run_cmd(cmd))


def t2_10_corpus_verify() -> dict[str, Any]:
    return worker_result("T2-10", "CorpusVerify", "BUILD", run_cmd([sys.executable, "scripts/verify_phase6_corpus.py"]))


# ---------------------------------------------------------------------------
# Team 3 — SHIP
# ---------------------------------------------------------------------------

def t3_1_p7_mission(apply: bool) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/taylor_phase7_mission.py"]
    if apply:
        cmd.append("--apply")
    return worker_result("T3-1", "P7Mission", "SHIP", run_cmd(cmd))


def t3_2_p8_mission(apply: bool) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/taylor_phase8_mission.py"]
    if apply:
        cmd.append("--apply")
    return worker_result("T3-2", "P8Mission", "SHIP", run_cmd(cmd))


def t3_3_tracking_gate() -> dict[str, Any]:
    return worker_result("T3-3", "TrackingGate", "SHIP", run_cmd([sys.executable, "scripts/tracking.py", "gate"]))


def t3_4_release_readiness() -> dict[str, Any]:
    step = run_cmd([sys.executable, "scripts/release_readiness.py", "--audit"])
    verdict = None
    if GA_STATUS.exists():
        try:
            verdict = json.loads(GA_STATUS.read_text(encoding="utf-8")).get("verdict")
        except json.JSONDecodeError:
            pass
    ga_pass = verdict == "RELEASE_READY"
    return worker_result("T3-4", "ReleaseReadiness", "SHIP", {"pass": step["pass"] and ga_pass, "ga_verdict": verdict, "audit": step})


def t3_5_wasm_size() -> dict[str, Any]:
    return worker_result("T3-5", "WasmSize", "SHIP", run_cmd([sys.executable, "scripts/measure_wasm_size.py"]))


def t3_6_language_hardening() -> dict[str, Any]:
    return worker_result("T3-6", "LanguageHardening", "SHIP", run_cmd([sys.executable, "scripts/verify_language_hardening.py"]))


def t3_7_issue_audit() -> dict[str, Any]:
    return worker_result("T3-7", "IssueAudit", "SHIP", run_cmd([sys.executable, "scripts/taylor_issue_closer.py", "audit"]))


def t3_8_phase7_verify() -> dict[str, Any]:
    return worker_result("T3-8", "Phase7Verify", "SHIP", run_cmd([sys.executable, "scripts/verify_phase7_hardening.py"]))


def t3_9_phase8_verify() -> dict[str, Any]:
    return worker_result("T3-9", "Phase8Verify", "SHIP", run_cmd([sys.executable, "scripts/verify_phase8_launch.py", "--skip-url-check"]))


def t3_10_ops_team() -> dict[str, Any]:
    return worker_result("T3-10", "OpsTeam", "SHIP", run_cmd([sys.executable, "scripts/taylor_ops_team.py", "run", "--mode", "end-of-turn"]))


def run_team_sequential(workers: list[Callable[[], dict[str, Any]]]) -> list[dict[str, Any]]:
    results = []
    for fn in workers:
        results.append(fn())
    return results


def run_team_parallel(workers: list[Callable[[], dict[str, Any]]], max_workers: int = 8) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in workers}
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda r: r["id"])
    return results


def advance(*, apply: bool = False, skip_env: bool = False) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    teams: list[dict[str, Any]] = []

    # Team 1 — FOUNDATION (sequential)
    t1_workers: list[Callable[[], dict[str, Any]]] = []
    if not skip_env:
        t1_workers.append(t1_1_env_bootstrap)
    t1_workers.extend([
        t1_2_wasm_codegen_tests,
        t1_3_native_probe,
        t1_4_self_host_verify,
        lambda: t1_5_compiler_mission(apply),
        t1_6_p5_diagnose,
        t1_7_p5_preflight,
        t1_8_p5_verify,
        lambda: t1_9_p5_mission(apply),
        lambda: t1_10_issue_close(apply),
    ])
    t1_results = run_team_sequential(t1_workers)
    t1_ok = all(w["pass"] for w in t1_results)
    teams.append({"team": 1, "name": "FOUNDATION", "ok": t1_ok, "workers": t1_results})

    # Team 2 — BUILD (parallel innovations after gate preflight)
    t2_workers: list[Callable[[], dict[str, Any]]] = [t2_1_innovations_gate]
    t2_workers.extend([lambda w=wid, m=mod, p=path: t2_innovation_worker(w, m, p) for wid, mod, path in INNOVATIONS])
    t2_workers.extend([
        lambda: t2_9_p6_mission(apply),
        t2_10_corpus_verify,
    ])
    if t1_ok or apply:
        t2_results = run_team_parallel(t2_workers)
    else:
        t2_results = [{"id": f"T2-{i}", "name": "Skipped", "team": "BUILD", "pass": False, "skipped": True} for i in range(1, 11)]
    t2_ok = all(w.get("pass") for w in t2_results if not w.get("skipped"))
    teams.append({"team": 2, "name": "BUILD", "ok": t2_ok, "workers": t2_results})

    # Team 3 — SHIP (parallel)
    t3_workers: list[Callable[[], dict[str, Any]]] = [
        lambda: t3_1_p7_mission(apply),
        lambda: t3_2_p8_mission(apply),
        t3_3_tracking_gate,
        t3_4_release_readiness,
        t3_5_wasm_size,
        t3_6_language_hardening,
        t3_7_issue_audit,
        t3_8_phase7_verify,
        t3_9_phase8_verify,
        t3_10_ops_team,
    ]
    if (t1_ok and t2_ok) or apply:
        t3_results = run_team_parallel(t3_workers)
    else:
        t3_results = [{"id": f"T3-{i}", "name": "Skipped", "team": "SHIP", "pass": False, "skipped": True} for i in range(1, 11)]
    t3_ok = all(w.get("pass") for w in t3_results if not w.get("skipped"))

    ga_verdict = None
    ga_blockers: list[str] = []
    if GA_STATUS.exists():
        try:
            ga = json.loads(GA_STATUS.read_text(encoding="utf-8"))
            ga_verdict = ga.get("verdict")
            ga_blockers = ga.get("blockers", [])
        except json.JSONDecodeError:
            pass

    all_workers = t1_results + t2_results + t3_results
    complete = ga_verdict == "RELEASE_READY"

    result = {
        "run_id": run_id,
        "owner": "TaylorCompiler30",
        "goal": "Compiler completion → RELEASE_READY",
        "ga_target": "RELEASE_READY",
        "complete": complete,
        "teams_ok": {"FOUNDATION": t1_ok, "BUILD": t2_ok, "SHIP": t3_ok},
        "workers_total": 30,
        "workers_pass": sum(1 for w in all_workers if w.get("pass")),
        "ga_verdict": ga_verdict,
        "ga_blockers": ga_blockers,
        "apply": apply,
        "updated_at": utc_now(),
        "teams": teams,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    return result


def write_report(result: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Taylor Compiler 30 Report",
        "",
        f"**Run ID:** {result.get('run_id')}  ",
        f"**Updated:** {result.get('updated_at')}  ",
        f"**Complete:** {result.get('complete')}  ",
        f"**Workers pass:** {result.get('workers_pass')}/{result.get('workers_total')}  ",
        f"**GA verdict:** `{result.get('ga_verdict')}`  ",
        "",
    ]
    for team in result.get("teams", []):
        lines.extend([
            f"## Team {team['team']} — {team['name']} ({'PASS' if team.get('ok') else 'FAIL'})",
            "",
            "| ID | Name | Pass |",
            "|----|------|------|",
        ])
        for w in team.get("workers", []):
            status = "SKIP" if w.get("skipped") else ("PASS" if w.get("pass") else "FAIL")
            lines.append(f"| {w['id']} | {w['name']} | {status} |")
        lines.append("")
    if result.get("ga_blockers"):
        lines.extend([
            "## GA blockers",
            "",
            f"`{result.get('ga_blockers')}`",
            "",
        ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Compiler 30 — 3 teams × 10 workers")
    sub = p.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="execute full 30-worker pipeline")
    run_p.add_argument("--apply", action="store_true", help="close eligible GitHub issues")
    run_p.add_argument("--skip-env", action="store_true", help="skip T1-1 env bootstrap")
    args = p.parse_args()

    if args.cmd == "run":
        result = advance(apply=args.apply, skip_env=args.skip_env)
        print(json.dumps({
            "complete": result["complete"],
            "ga_verdict": result["ga_verdict"],
            "workers_pass": result["workers_pass"],
            "teams_ok": result["teams_ok"],
            "report": str(REPORT.relative_to(ROOT)),
            "manifest": str(MANIFEST.relative_to(ROOT)),
        }, indent=2))
        return 0 if result["complete"] else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
