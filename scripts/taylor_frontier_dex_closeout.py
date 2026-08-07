#!/usr/bin/env python3
"""
Taylor Worker Crew — Frontier-DEX project close-out orchestrator.

Runs four parallel verification workers, independently validates results,
then seals the project via frontier-dex/closeout.sh.

Usage:
  python3 scripts/taylor_frontier_dex_closeout.py           # dry-run verify only
  python3 scripts/taylor_frontier_dex_closeout.py --close   # verify + closeout
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEX = ROOT / "frontier-dex"
REPORT = ROOT / "audit_reports" / "frontier_dex_closeout_report.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cmd(cmd: list[str], timeout: int = 600) -> dict[str, Any]:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return {
            "command": " ".join(cmd),
            "pass": r.returncode == 0,
            "exit_code": r.returncode,
            "output_tail": out[-2000:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"command": " ".join(cmd), "pass": False, "exit_code": -1, "output_tail": str(exc)}


WORKERS: dict[str, list[str]] = {
    "Taylor-1 (unit + integration)": ["cargo", "test", "-p", "frontier-dex"],
    "Taylor-2 (verify gates)": [sys.executable, "scripts/verify_frontier_dex.py"],
    "Taylor-3 (dex-hybrid module)": [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, 'build'); "
        "from arc_orchestrator import verify_dex_hybrid; "
        "raise SystemExit(verify_dex_hybrid())",
    ],
    "Taylor-4 (CLI + fixture)": [
        "cargo",
        "run",
        "--quiet",
        "--bin",
        "frontier",
        "--",
        "dex",
        "decompile",
        "--input",
        str(DEX / "tests" / "fixtures" / "minimal.dex"),
    ],
}


def run_crew() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(run_cmd, cmd): name for name, cmd in WORKERS.items()
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            result = future.result()
            result["worker"] = name
            results.append(result)
    return sorted(results, key=lambda r: r["worker"])


def render_report(results: list[dict[str, Any]], closed: bool) -> str:
    all_pass = all(r["pass"] for r in results)
    seal = "CLOSED" if closed and all_pass else ("READY" if all_pass else "BLOCKED")
    lines = [
        "# Frontier-DEX Taylor Worker Crew — Close-out Report",
        "",
        f"**Generated:** {utc_now()}",
        f"**Seal:** {seal}",
        "",
        "## Worker Results",
        "",
        "| Worker | Status | Command |",
        "|--------|--------|---------|",
    ]
    for r in results:
        mark = "✅ PASS" if r["pass"] else "❌ FAIL"
        lines.append(f"| {r['worker']} | {mark} | `{r['command'][:60]}…` |")
    lines.extend(["", "## Output Tails", ""])
    for r in results:
        lines.extend([f"### {r['worker']}", "", "```", r["output_tail"] or "(empty)", "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Taylor worker crew — Frontier-DEX close-out")
    parser.add_argument("--close", action="store_true", help="Run verify.sh + closeout.sh after crew passes")
    args = parser.parse_args()

    print("Taylor Worker Crew — Frontier-DEX close-out")
    print("=" * 50)
    results = run_crew()
    all_pass = all(r["pass"] for r in results)

    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['worker']}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    closed = False

    if all_pass and args.close:
        print("\nAll workers passed — running verify.sh + closeout.sh ...")
        v = run_cmd(["bash", str(DEX / "verify.sh")])
        c = run_cmd(["bash", str(DEX / "closeout.sh")]) if v["pass"] else {"pass": False, "exit_code": 1, "output_tail": "skipped"}
        results.extend([
            {"worker": "verify.sh", **v},
            {"worker": "closeout.sh", **c},
        ])
        closed = v["pass"] and c["pass"]
        all_pass = closed

    REPORT.write_text(render_report(results, closed), encoding="utf-8")
    print(f"\nReport: {REPORT.relative_to(ROOT)}")
    print(json.dumps({"ok": all_pass, "closed": closed, "workers": len(WORKERS)}, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
