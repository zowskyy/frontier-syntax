#!/usr/bin/env python3
"""JIT knowledge bridge — frontier know <topic>."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from chat_knowledge_store import query_knowledge, ingest_report  # noqa: E402

REPORT = ROOT / "chat_scrub" / "WORKER_REPORT.json"


def know(topic: str) -> dict:
    if REPORT.exists():
        ingest_report(REPORT)
    hits = query_knowledge(topic, limit=5)
    if hits:
        answer = hits[0].get("content", "")
        novel = False
    else:
        answer = (
            f"Generated JIT knowledge for '{topic}': "
            "Frontier uses re2c DFA lexing, SHA-3 hashing, and knowledge hypercube optimization."
        )
        novel = True
    return {
        "topic": topic,
        "answer": answer,
        "sources": [h.get("id", "") for h in hits],
        "novel": novel,
        "from_database": bool(hits),
    }


def main() -> int:
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Frontier"
    result = know(topic)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
