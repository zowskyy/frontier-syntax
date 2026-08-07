#!/usr/bin/env python3
"""
Agent shadow worker — maintains audit log during idle gaps and syncs to private repo.

HONESTY: This script only runs when YOU or a scheduler invoke it.
It does not run inside the LLM between chat turns.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "activity.json"
IDLE_SECONDS = int(os.environ.get("AUDIT_IDLE_SECONDS", "300"))  # 5 minutes
REMOTE = os.environ.get(
    "AUDIT_REMOTE", "https://github.com/zowskyy/frontier-agent-legal-record.git"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def idle_seconds() -> float | None:
    if not STATE.exists():
        return None
    data = json.loads(STATE.read_text(encoding="utf-8"))
    last = parse_ts(data.get("last_activity_utc"))
    if not last:
        return None
    return (datetime.now(timezone.utc) - last).total_seconds()


def run_logger_record(**kwargs: str) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "agent_audit_logger.py"),
        "record",
        "--category",
        kwargs.get("category", "idle_flush"),
        "--action",
        kwargs["action"],
        "--why",
        kwargs["why"],
        "--command",
        kwargs.get("command", str(ROOT / "scripts" / "agent_shadow_worker.py") + " run"),
        "--script",
        "agent-legal-record/scripts/agent_shadow_worker.py",
        "--skill",
        "agent-audit-record",
    ]
    if kwargs.get("verified") == "true":
        cmd.append("--verified")
    for o in kwargs.get("omissions", "").split("|"):
        if o.strip():
            cmd.extend(["--omission", o.strip()])
    subprocess.run(cmd, cwd=ROOT.parent, check=False)


def git_sync(commit_message: str) -> dict[str, str]:
    result = {"commit": "", "push": "", "error": ""}
    if not (ROOT / ".git").exists():
        result["error"] = "agent-legal-record is not a git repo yet"
        return result
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, capture_output=True)
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
        )
        if not status.stdout.strip():
            result["commit"] = "nothing to commit"
            return result
        subprocess.run(
            ["git", "commit", "-m", commit_message], cwd=ROOT, check=True, capture_output=True
        )
        result["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
        if REMOTE:
            push = subprocess.run(
                ["git", "push", "-u", "origin", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            result["push"] = "ok" if push.returncode == 0 else push.stderr[:200]
    except subprocess.CalledProcessError as e:
        result["error"] = (e.stderr or e.stdout or str(e))[:300]
    return result


def cmd_run(args: argparse.Namespace) -> int:
    idle = idle_seconds()
    actions: list[str] = []

    # Always update heartbeat
    run_logger_record(
        category="idle_flush",
        action="Shadow worker heartbeat",
        why="Scheduled or manual shadow worker run to maintain audit continuity",
        verified="true",
    )
    actions.append("heartbeat_logged")

    if idle is not None and idle >= IDLE_SECONDS:
        run_logger_record(
            category="idle_flush",
            action=f"Idle gap detected ({int(idle)}s since last activity)",
            why=(
                f"No user prompt for >= {IDLE_SECONDS}s; recording idle state "
                "so the legal record shows gaps explicitly (not hidden)"
            ),
            omissions="Did not execute new compiler work during idle — only logged gap",
        )
        actions.append(f"idle_gap_{int(idle)}s")

    if args.sync:
        sync = git_sync(args.message or f"audit: shadow worker sync {utc_now()}")
        run_logger_record(
            category="git",
            action="Git sync audit record",
            why="Push append-only session logs to private remote for owner backup",
            verified="true" if not sync.get("error") else "false",
            omissions=sync.get("error", ""),
        )
        actions.append(f"sync:{sync.get('commit','skip')}")

    print(json.dumps({"idle_seconds": idle, "actions": actions, "utc": utc_now()}, indent=2))
    return 0


def cmd_install_cron(args: argparse.Namespace) -> int:
    """Print cron line — user must install manually."""
    line = (
        f"*/5 * * * * cd {ROOT.parent} && "
        f"AUDIT_REMOTE={REMOTE} python3 {ROOT}/scripts/agent_shadow_worker.py run --sync "
        f">> {ROOT}/state/shadow_worker.log 2>&1"
    )
    print("# Add this to your crontab (crontab -e):")
    print(line)
    print()
    print("# HONESTY: Cron runs on YOUR machine/VM, not inside the LLM.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Agent shadow worker")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Heartbeat + optional idle gap log + sync")
    r.add_argument("--sync", action="store_true", help="git commit and push")
    r.add_argument("--message", default="")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("install-cron", help="Show cron line for 5-min idle flush")
    c.set_defaults(func=cmd_install_cron)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
