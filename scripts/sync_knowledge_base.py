#!/usr/bin/env python3
"""Ingest process_log.fr and swarm manifests into knowledge hypercube."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESS_LOG = ROOT / "docs" / "process_log.fr"
KNOWLEDGE = ROOT / "src" / "knowledge" / "hypercube" / "chat_knowledge.json"
MANIFEST_DIR = ROOT / "manifest"


def parse_process_entries(text: str) -> list[dict]:
    entries = []
    for block in re.findall(r"component ProcessEntry_\w+\s*\{([^}]+)\}", text, re.DOTALL):
        entry = {}
        for line in block.strip().splitlines():
            line = line.strip().rstrip(",")
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"')
            entry[key] = val
        if entry.get("process"):
            entries.append(entry)
    return entries


def sync_knowledge() -> dict:
    if not KNOWLEDGE.exists():
        return {"pass": False, "error": "knowledge file missing"}

    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    entries = data.get("entries", [])

    # Ingest process log
    if PROCESS_LOG.exists():
        log_entries = parse_process_entries(PROCESS_LOG.read_text(encoding="utf-8"))
        for i, le in enumerate(log_entries):  # full process log history
            eid = f"swarm_process_{le.get('process', i)}_{i}"
            if any(e.get("id") == eid for e in entries):
                continue
            entries.append({
                "id": eid,
                "category": "swarm_optimization",
                "title": f"Swarm: {le.get('process', 'unknown')}",
                "content": f"Decision: {le.get('decision', '')}. Result: {le.get('result', '')}.",
                "tags": ["swarm", "process_log", "llm_training"],
                "severity": "info",
                "source": "docs/process_log.fr",
            })

    # Ingest manifests (dedupe by id)
    existing_ids = {e.get("id") for e in entries}
    for mf in MANIFEST_DIR.glob("*.json"):
        eid = f"manifest_{mf.stem}"
        if eid in existing_ids:
            continue
        try:
            manifest = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries.append({
            "id": eid,
            "category": "manifest",
            "title": f"Manifest: {mf.stem}",
            "content": json.dumps(manifest, indent=0)[:500],
            "tags": ["manifest", "swarm", "conclusion"],
            "severity": "info",
            "source": str(mf.relative_to(ROOT)),
        })

    data["entries"] = entries
    data["entry_count"] = len(entries)
    data["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    KNOWLEDGE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"pass": True, "entries": len(entries), "ingested_log": PROCESS_LOG.exists()}


def main() -> int:
    result = sync_knowledge()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
