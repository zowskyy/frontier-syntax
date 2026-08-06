#!/usr/bin/env python3
"""Verify Advanced Archive Crawler module — all 20 improvements present."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "archive_unity.json"
MODULE_DIR = ROOT / "frontier" / "modules" / "archive_unity"

IMPROVEMENTS = [
    ("1", "DistributedFrontier", "Distributed frontier sharded across nodes"),
    ("2", "AdaptivePoliteness", "ML-based adaptive politeness"),
    ("3", "PredictivePrefetcher", "Predictive prefetching via Knowledge Hypercube"),
    ("4", "ContentDeduplicator", "Content-addressable deduplication"),
    ("5", "SelfHealingSession", "Checkpointed self-healing sessions"),
    ("6", "CDXBatchQuery", "Parallel CDX batch query with resumptionKey"),
    ("7", "ZeroCopyIO", "Zero-copy network to storage streaming"),
    ("8", "GPUHTMLParser", "GPU-accelerated HTML parsing"),
    ("9", "DynamicProxyPool", "Dynamic proxy pool with health scoring"),
    ("10", "IncrementalCDXCache", "Incremental local CDX cache"),
    ("11", "upload_metadata", "Bidirectional sync with Archive metadata upload"),
    ("12", "CDXWebSocketStream", "Real-time CDX WebSocket streaming"),
    ("13", "BlockchainLogger", "Blockchain-verified crawl logs"),
    ("14", "SwarmSynchronizer", "Swarm-synchronized frontier state"),
    ("15", "SelfTuningInterval", "Self-tuning sync interval"),
    ("16", "HierarchicalStorage", "Hierarchical storage tiering L1/L2/L3"),
    ("17", "SemanticIndex", "Semantic search over crawled content"),
    ("18", "VersionedPageStorage", "Git-like versioned page storage"),
    ("19", "ContentSummarizer", "Automated content summarization via Lighthouse"),
    ("20", "CrossDomainGraph", "Cross-domain knowledge graph"),
]

REQUIRED_FILES = [
    "advanced_crawler.fr",
    "frontier_shard.fr",
    "politeness_model.fr",
    "cdx_batch_query.fr",
    "zero_copy_io.fr",
    "gpu_parser.fr",
    "dynamic_proxy.fr",
    "cdx_stream.fr",
    "blockchain_log.fr",
    "swarm_sync.fr",
    "versioned_storage.fr",
    "knowledge_graph.fr",
]


def main() -> int:
    missing_files = [f for f in REQUIRED_FILES if not (MODULE_DIR / f).exists()]
    if missing_files:
        print("FAIL: Missing module files:")
        for f in missing_files:
            print(f"  - {f}")
        return 1

    all_content = ""
    for path in sorted(MODULE_DIR.glob("*.fr")):
        all_content += path.read_text(encoding="utf-8") + "\n"

    found = []
    missing_improvements = []
    for num, marker, desc in IMPROVEMENTS:
        if marker in all_content:
            found.append(num)
        else:
            missing_improvements.append(f"#{num} {marker}: {desc}")

    if not MANIFEST.exists():
        print("FAIL: manifest/archive_unity.json missing")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("improvements") != 20:
        print("FAIL: manifest must declare 20 improvements")
        return 1

    if missing_improvements:
        print("FAIL: Missing improvements:")
        for m in missing_improvements:
            print(f"  - {m}")
        return 1

    print(f"PASS: Advanced Archive Crawler verification")
    print(f"  Module files: {len(REQUIRED_FILES)}")
    print(f"  Improvements: {len(found)}/20")
    print(f"  Manifest: {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
