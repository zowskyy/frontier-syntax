#!/usr/bin/env python3
"""One-time scrub: remove user_prompt_excerpt from committed session files."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SESSIONS = REPO / "docs" / "agent_audit_log" / "sessions"
PRIVATE = REPO / "docs" / "agent_audit_log" / "state" / "private_prompts.jsonl"


def entry_hash(entry: dict) -> str:
    payload = {k: v for k, v in entry.items() if k != "entry_hash"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def scrub_file(path: Path) -> tuple[int, int]:
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out_lines: list[str] = []
    moved = 0
    prev_hash: str | None = None

    for line in lines:
        if not line.strip():
            continue
        entry = json.loads(line)
        excerpt = entry.pop("user_prompt_excerpt", None)
        honesty = entry.setdefault("honesty", {})
        honesty.setdefault("omissions", [])
        honesty.setdefault("cannot_verify", [])
        honesty.setdefault("verified_by_execution", False)
        if excerpt:
            moved += 1
            sha = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            entry["user_prompt_sha256"] = sha
            with PRIVATE.open("a", encoding="utf-8") as pf:
                pf.write(
                    json.dumps(
                        {
                            "entry_id": entry.get("id"),
                            "sha256": sha,
                            "excerpt": excerpt,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        if prev_hash:
            entry["prev_hash"] = prev_hash
        elif "prev_hash" in entry and not prev_hash:
            entry.pop("prev_hash", None)
        entry["entry_hash"] = entry_hash(entry)
        prev_hash = entry["entry_hash"]
        out_lines.append(json.dumps(entry, ensure_ascii=False))

    path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    return len(out_lines), moved


def main() -> int:
    total = moved = 0
    for path in sorted(SESSIONS.glob("*.jsonl")):
        n, m = scrub_file(path)
        total += n
        moved += m
        print(f"scrubbed {path.name}: {n} entries, {m} prompts relocated")
    print(f"done: {total} entries, {moved} prompts -> state/private_prompts.jsonl (gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
