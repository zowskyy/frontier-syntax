#!/usr/bin/env python3
"""
Shadow worker — heartbeat, idle-gap logging, README refresh, optional gathers.

Runs only when invoked (cron or end-of-turn). Not an LLM daemon.

Default `run` always refreshes README live-status blocks via update_audit_readme.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "docs" / "agent_audit_log"
STATE = AUDIT / "state" / "activity.json"
LOGGER = REPO / "scripts" / "agent_audit_logger.py"
GATHER = REPO / "scripts" / "gather_for_review.sh"
ECOSYSTEM = REPO / "scripts" / "gather_ecosystem_knowledge.py"
README_UPDATER = REPO / "scripts" / "update_audit_readme.py"
IDLE_SECONDS = 300


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_record(**kwargs: str) -> None:
    cmd = [
        sys.executable,
        str(LOGGER),
        "record",
        "--category",
        kwargs.get("category", "idle_flush"),
        "--action",
        kwargs["action"],
        "--why",
        kwargs["why"],
        "--script",
        "scripts/agent_shadow_worker.py",
        "--verified",
    ]
    if kwargs.get("omissions"):
        for o in kwargs["omissions"].split("|"):
            if o.strip():
                cmd.extend(["--omission", o.strip()])
    subprocess.run(cmd, cwd=REPO, check=False)


def idle_seconds() -> float | None:
    if not STATE.exists():
        return None
    data = json.loads(STATE.read_text(encoding="utf-8"))
    last = data.get("last_activity_utc")
    if not last:
        return None
    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - last_dt).total_seconds()


def refresh_readmes() -> dict:
    if not README_UPDATER.exists():
        return {"error": "update_audit_readme.py missing"}
    r = subprocess.run(
        [sys.executable, str(README_UPDATER), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return {"error": r.stderr[:200]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"raw": r.stdout[:200]}


def refresh_repo_snapshot() -> str:
    if not GATHER.exists():
        return "gather script missing"
    r = subprocess.run(["bash", str(GATHER)], cwd=REPO, capture_output=True, text=True)
    snap = AUDIT / "repo_snapshots" / "LATEST.txt"
    if snap.exists():
        return snap.read_text(encoding="utf-8").strip()
    return "ok" if r.returncode == 0 else r.stderr[:200]


def refresh_ecosystem_knowledge() -> str:
    if not ECOSYSTEM.exists():
        return "ecosystem gather script missing"
    r = subprocess.run(
        [sys.executable, str(ECOSYSTEM), "--fast"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    latest = AUDIT / "ecosystem_knowledge" / "LATEST.txt"
    if latest.exists():
        return latest.read_text(encoding="utf-8").strip()
    return "ok" if r.returncode == 0 else r.stderr[:200]


def cmd_run(args: argparse.Namespace) -> int:
    idle = idle_seconds()
    actions = []

    log_record(
        category="idle_flush",
        action="Shadow worker heartbeat",
        why="Maintain audit continuity; owner reviews docs/agent_audit_log/",
    )
    actions.append("heartbeat")

    if idle is not None and idle >= IDLE_SECONDS:
        log_record(
            category="idle_flush",
            action=f"Idle gap {int(idle)}s recorded",
            why=f"No logged activity for >= {IDLE_SECONDS}s; gap is explicit in audit trail",
            omissions="No new compiler work during idle",
        )
        actions.append("idle_gap")

    if not args.no_readme:
        readme_result = refresh_readmes()
        changed = [
            k for k, v in readme_result.get("files", {}).items() if v
        ]
        log_record(
            category="tool_call",
            action="Refreshed README live-status blocks",
            why="Owner policy: shadow worker keeps README audit/blueprint status current",
            omissions="" if changed else "README markers unchanged",
        )
        actions.append(f"readme:{','.join(changed) or 'unchanged'}")

    if args.snapshot:
        path = refresh_repo_snapshot()
        log_record(
            category="tool_call",
            action="Refreshed repo snapshot via gather_for_review.sh",
            why="Owner requested in-repo copy of structure, files, workers, build output",
            omissions="" if path else "gather may have failed",
        )
        actions.append(f"snapshot:{path}")

    if args.ecosystem:
        run_id = refresh_ecosystem_knowledge()
        log_record(
            category="tool_call",
            action="Refreshed ecosystem knowledge report",
            why="Multi-repo claims vs blueprint status for owner review",
            omissions="" if run_id else "ecosystem gather may have failed",
        )
        actions.append(f"ecosystem:{run_id}")
        if not args.no_readme:
            refresh_readmes()
            actions.append("readme:post-ecosystem")

    print(json.dumps({"idle_seconds": idle, "actions": actions, "utc": utc_now()}, indent=2))
    return 0


def cmd_install_cron(args: argparse.Namespace) -> int:
    line = (
        f"*/5 * * * * cd {REPO} && python3 scripts/agent_shadow_worker.py run "
        f">> docs/agent_audit_log/state/shadow_worker.log 2>&1"
    )
    print("# Add to crontab -e (heartbeat + README refresh every 5 min):")
    print(line)
    print("# Full weekly refresh:")
    print(
        f"0 6 * * 0 cd {REPO} && python3 scripts/agent_shadow_worker.py run "
        f"--ecosystem --snapshot >> docs/agent_audit_log/state/shadow_worker.log 2>&1"
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--snapshot", action="store_true", help="run gather_for_review.sh")
    r.add_argument("--ecosystem", action="store_true", help="run gather_ecosystem_knowledge.py --fast")
    r.add_argument("--no-readme", action="store_true", help="skip README live-status refresh")
    r.set_defaults(func=cmd_run)
    c = sub.add_parser("install-cron")
    c.set_defaults(func=cmd_install_cron)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
