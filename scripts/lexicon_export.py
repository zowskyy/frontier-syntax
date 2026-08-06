#!/usr/bin/env python3
"""Export Lexicon for LLM training and research."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEXICON_LOG = ROOT / "docs" / "lexicon_log.fr"
EXPORT_JSON = ROOT / "manifest" / "lexicon_export.json"
EXPORT_JSONL = ROOT / "manifest" / "lexicon_export.jsonl"


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


def export_lexicon() -> dict:
    entries = []
    if LEXICON_LOG.exists():
        entries = parse_lexicon_entries(LEXICON_LOG.read_text(encoding="utf-8"))
    index_path = ROOT / "manifest" / "lexicon_index.json"
    if index_path.exists():
        try:
            idx = json.loads(index_path.read_text(encoding="utf-8"))
            seen = {e.get("action_id") for e in entries}
            for e in idx.get("entries", []):
                if e.get("action_id") not in seen:
                    entries.append(e)
        except json.JSONDecodeError:
            pass

    training_records = []
    for e in entries:
        training_records.append({
            "instruction": f"Document Frontier lexicon action: {e.get('action_type', '')}",
            "input": e.get("documentation", ""),
            "output": json.dumps({
                "action_id": e.get("action_id"),
                "worker_id": e.get("worker_id"),
                "user_id": e.get("user_id"),
                "lexicon_entry": e.get("lexicon_entry"),
                "input_hash": e.get("input_hash"),
                "output_hash": e.get("output_hash"),
            }),
            "metadata": {
                "timestamp": e.get("timestamp"),
                "parent_action": e.get("parent_action"),
                "source": "lexicon_bound_worker",
            },
        })

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "entry_count": len(entries),
        "training_records": len(training_records),
        "entries": entries,
        "training": training_records,
    }
    EXPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_JSON.write_text(json.dumps(export, indent=2), encoding="utf-8")
    with open(EXPORT_JSONL, "w", encoding="utf-8") as f:
        for rec in training_records:
            f.write(json.dumps(rec) + "\n")

    return {
        "pass": True,
        "entries": len(entries),
        "training_records": len(training_records),
        "export_json": str(EXPORT_JSON.relative_to(ROOT)),
        "export_jsonl": str(EXPORT_JSONL.relative_to(ROOT)),
    }


def main() -> int:
    result = export_lexicon()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
