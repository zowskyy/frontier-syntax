#!/usr/bin/env python3
"""Bridge Knowledge Engine queries into Lighthouse stack context."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from chat_knowledge_store import ingest_report, query_knowledge  # noqa: E402

LIGHTHOUSE_DIR = ROOT / "frontier" / "lighthouse"
BRIDGE_OUT = ROOT / "frontier" / "lighthouse" / "knowledge_bridge.json"
REPORT = ROOT / "chat_scrub" / "WORKER_REPORT.json"

LIGHTHOUSE_QUERIES = [
    "attack vector security",
    "WASM codegen gap",
    "architecture component",
    "self-hosting",
    "IPFS import",
]


def main() -> int:
    if REPORT.exists():
        ingest_report(REPORT)

    bridge = {
        "version": "1.0.0",
        "source": "chat_knowledge_store",
        "lighthouse_modules": [],
        "knowledge_context": {},
    }

    if LIGHTHOUSE_DIR.exists():
        for spec in sorted(LIGHTHOUSE_DIR.glob("*.frontier")):
            bridge["lighthouse_modules"].append(spec.name)

    for query in LIGHTHOUSE_QUERIES:
        results = query_knowledge(query, limit=5)
        bridge["knowledge_context"][query] = results

    BRIDGE_OUT.write_text(json.dumps(bridge, indent=2), encoding="utf-8")
    print(f"✅ Lighthouse knowledge bridge: {BRIDGE_OUT.relative_to(ROOT)}")
    print(f"   Modules: {len(bridge['lighthouse_modules'])}")
    print(f"   Query contexts: {len(bridge['knowledge_context'])}")
    for query, hits in bridge["knowledge_context"].items():
        print(f"   - {query}: {len(hits)} hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
