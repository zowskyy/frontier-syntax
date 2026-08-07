#!/usr/bin/env python3
"""
Taylor Compiler Mission — autonomous self-hosting compiler work until 100% complete.

W2 CompilerCore runs this every production/daily cycle. Advances milestones,
records evidence, and signals owner only when mission.complete is true.
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
MISSION = ROOT / "manifest" / "compiler_self_host_mission.json"
REPORT = ROOT / "audit_reports" / "compiler_mission_report.md"

MILESTONES = [
    {
        "id": "M1",
        "name": "wasm_host_exports",
        "check": ["src/wasm_host_exports.rs", "src/bin/frontier_wasm_host.rs"],
        "verify": None,
    },
    {
        "id": "M2",
        "name": "native_self_host_probe",
        "verify": ["python3", "scripts/run_native_self_host.py"],
        "manifest": "manifest/native_self_host.json",
        "manifest_field": "pass",
    },
    {
        "id": "M3",
        "name": "verify_self_hosting_native",
        "verify": ["python3", "scripts/verify_self_hosting.py", "--native"],
        "manifest": "manifest/self_hosting_verify.json",
        "manifest_field": "native_pass",
    },
    {
        "id": "M4",
        "name": "close_issue_46",
        "verify": ["python3", "scripts/taylor_issue_closer.py", "audit"],
        "complete_when": "issue_46_closed",
    },
    {
        "id": "M5",
        "name": "phase5_full_compiler",
        "description": "Grow main.fr to full compiler; Phase 5 exit — optional long-horizon",
        "complete_when": "main_fr_full_compiler",
        "optional": True,
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_mission() -> dict[str, Any]:
    if MISSION.exists():
        return json.loads(MISSION.read_text(encoding="utf-8"))
    return {
        "version": "1.0.0",
        "owner": "W2_CompilerCore",
        "goal": "Frontier-native self-hosting — owner notified only when mission.complete",
        "complete": False,
        "milestones": {},
    }


def save_mission(data: dict[str, Any]) -> None:
    MISSION.parent.mkdir(parents=True, exist_ok=True)
    MISSION.write_text(json.dumps(data, indent=2), encoding="utf-8")


def gh_issue_open(num: int) -> bool:
    r = subprocess.run(
        ["gh", "issue", "view", str(num), "--json", "state"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return True
    return json.loads(r.stdout).get("state") == "OPEN"


def run_verify(cmd: list[str]) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return {
        "command": " ".join(cmd),
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output_tail": (r.stdout + r.stderr)[-600:],
    }


def evaluate_milestone(ms: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": ms["id"],
        "name": ms["name"],
        "pass": False,
        "optional": ms.get("optional", False),
    }

    if ms.get("check"):
        result["pass"] = all((ROOT / p).exists() for p in ms["check"])
        result["checks"] = ms["check"]
        return result

    if ms.get("complete_when") == "issue_46_closed":
        result["pass"] = not gh_issue_open(46)
        result["issue_46_open"] = not result["pass"]
        return result

    if ms.get("complete_when") == "main_fr_full_compiler":
        # Phase 5 — full compiler in main.fr (not required for owner Phase 1.3 relief)
        manifest_path = ROOT / "manifest" / "phase5_full_compiler.json"
        result["pass"] = False
        if manifest_path.exists():
            try:
                result["pass"] = bool(json.loads(manifest_path.read_text()).get("complete"))
            except json.JSONDecodeError:
                pass
        result["reason"] = "Phase 5 full main.fr compiler — workers continue in background"
        return result

    if ms.get("verify"):
        step = run_verify(ms["verify"])
        result["verify"] = step
        result["pass"] = step["pass"]
        if ms.get("manifest"):
            path = ROOT / ms["manifest"]
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    field = ms.get("manifest_field", "pass")
                    result["pass"] = bool(data.get(field)) and result["pass"]
                except json.JSONDecodeError:
                    result["pass"] = False
        return result

    result["pass"] = False
    return result


def advance(*, apply: bool = False) -> dict[str, Any]:
    mission = load_mission()
    results = []
    all_required_pass = True

    for ms in MILESTONES:
        ev = evaluate_milestone(ms)
        results.append(ev)
        mission["milestones"][ms["id"]] = {
            "name": ms["name"],
            "pass": ev["pass"],
            "updated_at": utc_now(),
        }
        if not ev.get("optional") and not ev["pass"]:
            all_required_pass = False

    # Required milestones: M1-M4 (not M5 optional Phase 5)
    required_ids = [m["id"] for m in MILESTONES if not m.get("optional")]
    mission["complete"] = all(
        mission["milestones"].get(mid, {}).get("pass") for mid in required_ids
    )
    mission["updated_at"] = utc_now()
    mission["last_run"] = {
        "apply": apply,
        "results": results,
        "owner_notify": mission["complete"],
    }

    if apply and not mission["complete"]:
        # Attempt issue close for #46 when M3 passes
        m3 = next((r for r in results if r["id"] == "M3"), None)
        if m3 and m3.get("pass"):
            subprocess.run(
                [sys.executable, "scripts/taylor_issue_closer.py", "close", "--worker", "W2_CompilerCore", "--apply"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    save_mission(mission)
    write_report(mission, results)
    return mission


def write_report(mission: dict[str, Any], results: list[dict[str, Any]]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Taylor Compiler Mission Report",
        "",
        f"**Updated:** {mission.get('updated_at')}  ",
        f"**Complete:** {mission.get('complete')}  ",
        f"**Owner notify:** {'YES — self-hosting done' if mission.get('complete') else 'NO — work continues'}  ",
        "",
        "## Milestones",
        "",
        "| ID | Name | Pass |",
        "|----|------|------|",
    ]
    for r in results:
        opt = " (optional)" if r.get("optional") else ""
        lines.append(f"| {r['id']} | {r['name']}{opt} | {'PASS' if r['pass'] else 'FAIL'} |")
    lines.append("")
    if mission.get("complete"):
        lines.append("> **Owner:** You no longer need to worry about self-hosting (#46). Taylor workers validated native path.")
    else:
        lines.append("> **Owner:** Mission in progress — workers continue each production run.")
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Compiler Mission")
    p.add_argument("--apply", action="store_true", help="attempt issue #46 close when native passes")
    args = p.parse_args()
    mission = advance(apply=args.apply)
    print(json.dumps({
        "complete": mission["complete"],
        "owner_notify": mission["complete"],
        "milestones": {k: v.get("pass") for k, v in mission.get("milestones", {}).items()},
        "report": str(REPORT.relative_to(ROOT)),
        "manifest": str(MISSION.relative_to(ROOT)),
    }, indent=2))
    return 0 if mission["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
