#!/usr/bin/env python3
"""
Append-only agent audit log — EVERY action, in-repo at docs/agent_audit_log/.

Required per entry: action, why, how_to_repeat, honesty (verified / omissions).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_ROOT = REPO_ROOT / "docs" / "agent_audit_log"
SESSIONS = AUDIT_ROOT / "sessions"
STATE_DIR = AUDIT_ROOT / "state"
INDEX = AUDIT_ROOT / "index.json"
MAX_ENTRY_BYTES = 8192

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"x-access-token:[^@\s]+"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*\S+"),
]

DEFAULT_SESSION = os.environ.get(
    "AGENT_AUDIT_SESSION", datetime.now(timezone.utc).strftime("%Y-%m-%d")
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(text: str) -> str:
    out = text
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def git_info() -> dict[str, str]:
    info: dict[str, str] = {}
    try:
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return info


def session_path(session_id: str) -> Path:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\-.]", "_", session_id)
    return SESSIONS / f"{safe}.jsonl"


def load_state() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = STATE_DIR / "activity.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"last_activity_utc": None, "session_id": DEFAULT_SESSION, "entry_count": 0}


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "activity.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_index(session_id: str, entry_id: str, action: str) -> None:
    idx: dict[str, Any] = {"sessions": {}, "updated_at": utc_now()}
    if INDEX.exists():
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
    s = idx.setdefault("sessions", {}).setdefault(
        session_id, {"entry_count": 0, "last_entry_id": None, "last_action": None}
    )
    s["entry_count"] = s.get("entry_count", 0) + 1
    s["last_entry_id"] = entry_id
    s["last_action"] = action
    idx["updated_at"] = utc_now()
    idx["repo_root"] = str(REPO_ROOT)
    idx["audit_root"] = str(AUDIT_ROOT.relative_to(REPO_ROOT))
    INDEX.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def record(
    *,
    session_id: str,
    category: str,
    action: str,
    why: str,
    command: str = "",
    script: str = "",
    skill: str = "agent-audit-record",
    tool: str = "",
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
    exit_code: int | None = None,
) -> dict[str, Any]:
    entry_id = str(uuid.uuid4())
    gi = git_info()

    safe_inputs = json.loads(redact(json.dumps(inputs or {}, default=str)))
    safe_outputs = json.loads(redact(json.dumps(outputs or {}, default=str)))

    entry: dict[str, Any] = {
        "id": entry_id,
        "timestamp_utc": utc_now(),
        "session_id": session_id,
        "agent": {
            "type": os.environ.get("CURSOR_AGENT_TYPE", "cursor-cloud-agent"),
            "model": os.environ.get("CURSOR_AGENT_MODEL", "composer"),
            "branch": gi.get("branch", ""),
            "commit": gi.get("commit", ""),
            "repo": "zowskyy/frontier-syntax",
        },
        "category": category,
        "tool": tool,
        "action": redact(action),
        "why": redact(why),
        "how_to_repeat": {
            "command": redact(command),
            "script": script,
            "skill": skill,
            "extension_hook": extension_hook,
            "prerequisites": prerequisites or [],
        },
        "inputs": safe_inputs,
        "outputs": safe_outputs,
        "artifacts": artifacts or [],
        "exit_code": exit_code,
        "git": gi,
        "honesty": {
            "verified_by_execution": verified,
            "omissions": omissions or [],
            "cannot_verify": cannot_verify or [],
        },
        "user_prompt_excerpt": redact(user_prompt_excerpt[:500]),
        "parent_id": parent_id,
    }

    line = json.dumps(entry, ensure_ascii=False)
    if len(line.encode("utf-8")) > MAX_ENTRY_BYTES:
        entry["outputs"] = {"truncated": True, "sha256": hashlib.sha256(line.encode()).hexdigest()}
        line = json.dumps(entry, ensure_ascii=False)

    path = session_path(session_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    state = load_state()
    state["last_activity_utc"] = entry["timestamp_utc"]
    state["session_id"] = session_id
    state["entry_count"] = state.get("entry_count", 0) + 1
    save_state(state)
    update_index(session_id, entry_id, action)
    return entry


def cmd_record(args: argparse.Namespace) -> int:
    entry = record(
        session_id=args.session or DEFAULT_SESSION,
        category=args.category,
        action=args.action,
        why=args.why,
        command=args.command or "",
        script=args.script or "",
        skill=args.skill or "agent-audit-record",
        tool=args.tool or "",
        extension_hook=args.extension_hook or "",
        prerequisites=args.prerequisite or [],
        inputs=json.loads(args.inputs) if args.inputs else {},
        outputs=json.loads(args.outputs) if args.outputs else {},
        artifacts=args.artifact or [],
        verified=args.verified,
        omissions=args.omission or [],
        cannot_verify=args.cannot_verify or [],
        user_prompt_excerpt=args.user_prompt or "",
        exit_code=args.exit_code,
    )
    print(json.dumps(entry, indent=2))
    return 0


def cmd_tail(args: argparse.Namespace) -> int:
    sid = args.session or DEFAULT_SESSION
    path = session_path(sid)
    if not path.exists():
        print(f"No session: {path}", file=sys.stderr)
        return 1
    for line in path.read_text(encoding="utf-8").strip().splitlines()[-args.n :]:
        print(line)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Agent audit logger (every action)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record")
    r.add_argument("--session", default=DEFAULT_SESSION)
    r.add_argument("--category", required=True)
    r.add_argument("--action", required=True)
    r.add_argument("--why", required=True)
    r.add_argument("--command", default="")
    r.add_argument("--script", default="")
    r.add_argument("--skill", default="agent-audit-record")
    r.add_argument("--tool", default="")
    r.add_argument("--extension-hook", default="")
    r.add_argument("--prerequisite", action="append", default=[])
    r.add_argument("--inputs", default="")
    r.add_argument("--outputs", default="")
    r.add_argument("--artifact", action="append", default=[])
    r.add_argument("--verified", action="store_true")
    r.add_argument("--omission", action="append", default=[])
    r.add_argument("--cannot-verify", action="append", default=[])
    r.add_argument("--user-prompt", default="")
    r.add_argument("--exit-code", type=int, default=None)
    r.set_defaults(func=cmd_record)

    t = sub.add_parser("tail")
    t.add_argument("--session", default=DEFAULT_SESSION)
    t.add_argument("-n", type=int, default=20)
    t.set_defaults(func=cmd_tail)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
