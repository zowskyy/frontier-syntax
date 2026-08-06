#!/usr/bin/env python3
"""
Agent audit logger — append-only legal/personal record of agent actions.

Every entry requires: action, why, how_to_repeat, honesty block.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SESSIONS = ROOT / "sessions"
STATE = ROOT / "state"
INDEX = ROOT / "index.json"
DEFAULT_SESSION = os.environ.get("AGENT_AUDIT_SESSION", "frontier-syntax-main")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_info() -> dict[str, str]:
    info: dict[str, str] = {}
    try:
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT.parent, text=True
        ).strip()
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT.parent, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return info


def session_path(session_id: str) -> Path:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    return SESSIONS / f"{session_id}.jsonl"


def load_state() -> dict[str, Any]:
    STATE.mkdir(parents=True, exist_ok=True)
    p = STATE / "activity.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"last_activity_utc": None, "last_user_prompt_utc": None, "session_id": DEFAULT_SESSION}


def save_state(state: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "activity.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_index(session_id: str, entry_id: str, action: str) -> None:
    idx: dict[str, Any] = {"sessions": {}, "updated_at": utc_now()}
    if INDEX.exists():
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
    sessions = idx.setdefault("sessions", {})
    s = sessions.setdefault(session_id, {"entry_count": 0, "last_entry_id": None, "last_action": None})
    s["entry_count"] = s.get("entry_count", 0) + 1
    s["last_entry_id"] = entry_id
    s["last_action"] = action
    idx["updated_at"] = utc_now()
    INDEX.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def record(
    *,
    session_id: str,
    category: str,
    action: str,
    why: str,
    command: str = "",
    script: str = "",
    skill: str = "",
    extension_hook: str = "",
    prerequisites: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    verified: bool = False,
    omissions: list[str] | None = None,
    cannot_verify: list[str] | None = None,
    user_prompt_excerpt: str = "",
    parent_id: str = "",
    also_process_log: bool = False,
    pr_url: str = "",
) -> dict[str, Any]:
    entry_id = str(uuid.uuid4())
    gi = git_info()
    entry: dict[str, Any] = {
        "id": entry_id,
        "timestamp_utc": utc_now(),
        "session_id": session_id,
        "agent": {
            "type": os.environ.get("CURSOR_AGENT_TYPE", "cursor-cloud-agent"),
            "model": os.environ.get("CURSOR_AGENT_MODEL", "composer"),
            "run_url": os.environ.get("CURSOR_AGENT_RUN_URL", ""),
            "branch": gi.get("branch", ""),
            "repo": "zowskyy/frontier-syntax",
        },
        "category": category,
        "action": action,
        "why": why,
        "how_to_repeat": {
            "command": command,
            "script": script,
            "skill": skill,
            "extension_hook": extension_hook,
            "prerequisites": prerequisites or [],
        },
        "inputs": inputs or {},
        "outputs": outputs or {},
        "artifacts": artifacts or [],
        "git": {**gi, "pr_url": pr_url},
        "honesty": {
            "verified_by_execution": verified,
            "omissions": omissions or [],
            "cannot_verify": cannot_verify or [],
        },
        "user_prompt_excerpt": user_prompt_excerpt[:500],
        "parent_id": parent_id,
    }

    path = session_path(session_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    state = load_state()
    state["last_activity_utc"] = entry["timestamp_utc"]
    if category == "user_prompt":
        state["last_user_prompt_utc"] = entry["timestamp_utc"]
    state["session_id"] = session_id
    save_state(state)
    update_index(session_id, entry_id, action)

    if also_process_log:
        _dual_write_process_log(action, why, outputs or {})

    return entry


def _dual_write_process_log(action: str, why: str, outputs: dict[str, Any]) -> None:
    try:
        sys.path.insert(0, str(ROOT.parent / "scripts"))
        from process_logger import ProcessLogger  # type: ignore

        logger = ProcessLogger(worker_id="agent_audit")
        logger.log("agent_audit", why, action, outputs)
    except Exception as e:
        # Never fail the audit log because process_log failed
        record(
            session_id=load_state().get("session_id", DEFAULT_SESSION),
            category="error",
            action="process_log dual-write failed",
            why="Attempted dual-write to docs/process_log.fr",
            verified=False,
            omissions=[str(e)],
        )


def cmd_record(args: argparse.Namespace) -> int:
    omissions = args.omission or []
    cannot = args.cannot_verify or []
    prereq = args.prerequisite or []
    artifacts = args.artifact or []
    entry = record(
        session_id=args.session or DEFAULT_SESSION,
        category=args.category,
        action=args.action,
        why=args.why,
        command=args.command or "",
        script=args.script or "",
        skill=args.skill or "",
        extension_hook=args.extension_hook or "",
        prerequisites=prereq,
        inputs=json.loads(args.inputs) if args.inputs else {},
        outputs=json.loads(args.outputs) if args.outputs else {},
        artifacts=artifacts,
        verified=args.verified,
        omissions=omissions,
        cannot_verify=cannot,
        user_prompt_excerpt=args.user_prompt or "",
        also_process_log=args.also_process_log,
        pr_url=args.pr_url or "",
    )
    print(json.dumps(entry, indent=2))
    return 0


def cmd_tail(args: argparse.Namespace) -> int:
    sid = args.session or DEFAULT_SESSION
    path = session_path(sid)
    if not path.exists():
        print(f"No session log: {path}", file=sys.stderr)
        return 1
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    for line in lines[-args.n :]:
        print(line)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Agent audit logger")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record", help="Append one audit entry")
    r.add_argument("--session", default=DEFAULT_SESSION)
    r.add_argument("--category", required=True)
    r.add_argument("--action", required=True)
    r.add_argument("--why", required=True)
    r.add_argument("--command", default="")
    r.add_argument("--script", default="")
    r.add_argument("--skill", default="")
    r.add_argument("--extension-hook", default="")
    r.add_argument("--prerequisite", action="append", default=[])
    r.add_argument("--inputs", default="")
    r.add_argument("--outputs", default="")
    r.add_argument("--artifact", action="append", default=[])
    r.add_argument("--verified", action="store_true")
    r.add_argument("--omission", action="append", default=[])
    r.add_argument("--cannot-verify", action="append", default=[])
    r.add_argument("--user-prompt", default="")
    r.add_argument("--also-process-log", action="store_true")
    r.add_argument("--pr-url", default="")
    r.set_defaults(func=cmd_record)

    t = sub.add_parser("tail", help="Show last N entries")
    t.add_argument("--session", default=DEFAULT_SESSION)
    t.add_argument("-n", type=int, default=10)
    t.set_defaults(func=cmd_tail)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
