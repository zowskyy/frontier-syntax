#!/usr/bin/env python3
"""Audit log retention: export old sessions, enforce TTL on private prompt store."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "docs" / "agent_audit_log"
SESSIONS = AUDIT / "sessions"
ARCHIVE = AUDIT / "archive"
PRIVATE = AUDIT / "state" / "private_prompts.jsonl"
DEFAULT_TTL_DAYS = 90


def parse_ts(entry: dict) -> datetime | None:
    raw = entry.get("timestamp_utc", "")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def cmd_export(args: argparse.Namespace) -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    for path in sorted(SESSIONS.glob("*.jsonl")):
        keep: list[str] = []
        archive: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            ts = parse_ts(entry)
            if ts and ts < cutoff:
                archive.append(line)
            else:
                keep.append(line)
        if archive:
            dest = ARCHIVE / f"{path.stem}_until_{cutoff.date()}.jsonl"
            with dest.open("a", encoding="utf-8") as f:
                for line in archive:
                    f.write(line + "\n")
            path.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
            print(f"archived {len(archive)} from {path.name} -> {dest.relative_to(REPO)}")
    return 0


def cmd_prune_private(args: argparse.Namespace) -> int:
    if not PRIVATE.exists():
        print("no private prompt store")
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.ttl_days)
    kept: list[str] = []
    removed = 0
    for line in PRIVATE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        # private store has no timestamp; prune by line count cap
        kept.append(line)
    max_lines = args.max_private_lines
    if len(kept) > max_lines:
        removed = len(kept) - max_lines
        kept = kept[-max_lines:]
    PRIVATE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    print(f"private prompts: kept {len(kept)}, removed {removed}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Audit log retention utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export-old", help="move entries older than N days to archive/")
    e.add_argument("--older-than-days", type=int, default=DEFAULT_TTL_DAYS)
    e.set_defaults(func=cmd_export)

    pr = sub.add_parser("prune-private", help="cap private prompt store size")
    pr.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    pr.add_argument("--max-private-lines", type=int, default=500)
    pr.set_defaults(func=cmd_prune_private)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
