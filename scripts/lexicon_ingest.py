#!/usr/bin/env python3
"""Ingest Lexicon log into knowledge hypercube for research and LLM training."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEXICON_LOG = ROOT / "docs" / "lexicon_log.fr"
KNOWLEDGE = ROOT / "src" / "knowledge" / "hypercube" / "chat_knowledge.json"
INDEX = ROOT / "manifest" / "lexicon_index.json"


def parse_lexicon_entries(text: str) -> list[dict]:
    entries = []
    for block in re.findall(r"component LexiconEntry_\w+\s*\{([^}]+)\}", text, re.DOTALL):
        entry = {}
        for line in block.strip().splitlines():
            line = line.strip().rstrip(",")
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            entry[key.strip()] = val.strip().strip('"')
        if entry.get("action_id"):
            entries.append(entry)
    return entries


def ingest() -> dict:
    if not KNOWLEDGE.exists():
        return {"pass": False, "error": "knowledge file missing"}

    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    kb_entries = data.get("entries", [])
    existing = {e.get("id") for e in kb_entries}

    lexicon_entries: list[dict] = []
    if LEXICON_LOG.exists():
        lexicon_entries = parse_lexicon_entries(LEXICON_LOG.read_text(encoding="utf-8"))
    if INDEX.exists():
        try:
            idx = json.loads(INDEX.read_text(encoding="utf-8"))
            for e in idx.get("entries", []):
                if e.get("action_id") and e["action_id"] not in {x.get("action_id") for x in lexicon_entries}:
                    lexicon_entries.append(e)
        except json.JSONDecodeError:
            pass

    added = 0
    for le in lexicon_entries:
        eid = f"lexicon_{le.get('action_id', '')}"
        if eid in existing:
            continue
        kb_entries.append({
            "id": eid,
            "category": "lexicon_bound",
            "title": f"Lexicon: {le.get('action_type', 'action')}",
            "content": (
                f"Worker {le.get('worker_id')}. "
                f"User {le.get('user_id', '')[:12]}... "
                f"Doc: {le.get('documentation', '')}. "
                f"Entry: {le.get('lexicon_entry', '')[:16]}..."
            ),
            "tags": ["lexicon", "bound", "worker", le.get("action_type", "")],
            "severity": "info",
            "source": "docs/lexicon_log.fr",
        })
        added += 1

    data["entries"] = kb_entries
    data["entry_count"] = len(kb_entries)
    data["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    KNOWLEDGE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"pass": True, "ingested": added, "total_lexicon": len(lexicon_entries), "kb_entries": len(kb_entries)}


def main() -> int:
    result = ingest()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
