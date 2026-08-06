#!/usr/bin/env python3
"""
16-worker Frontier swarm — analyze full account chat history for Peerless optimization.

Each worker receives a shard of account_history_corpus.json and extracts:
  - Frontier syntax optimization opportunities
  - Maintenance tasks
  - Code improvements
  - Performance targets

Outputs merged into manifest/peerless_implementation_plan.json and audit report.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_account_chat_history import build_corpus  # noqa: E402
from process_logger import ProcessLogger  # noqa: E402

CORPUS_PATH = ROOT / "chat_scrub" / "account_history_corpus.json"
MANIFEST = ROOT / "manifest" / "peerless_implementation_plan.json"
REPORT = ROOT / "audit_reports" / "peerless_implementation_plan.md"
WORKERS_DEFAULT = 16

# Theme detection for optimization classification
THEMES: list[tuple[str, list[str], str]] = [
    ("wasm_optimization", ["wasm", "binary", "size", "wasm-opt", "slim", "browser"], "src/wasm_codegen.rs"),
    ("codegen_depth", ["codegen", "let ", "if ", "while", "float", "string", "struct"], "src/wasm_codegen.rs"),
    ("self_hosting", ["self-host", "self host", "bootstrap", "main.fr", "native compile"], "frontier/src/main.fr"),
    ("knowledge_engine", ["knowledge", "hypercube", "implementation_hint", "algorithm"], "src/knowledge/hypercube/"),
    ("swarm_optimization", ["swarm", "worker", "parallel", "symbiotic", "tandem", "20x", "20×"], "scripts/swarm_optimized.py"),
    ("runtime_gpu", ["gpu", "vulkan", "cuda", "runtime"], "frontier/gpu/vulkan.fr"),
    ("runtime_ipfs", ["ipfs", "cid", "gateway", "decentralized"], "frontier/ipfs/swarm.fr"),
    ("runtime_cdx", ["cdx", "streaming", "archive", "wayback"], "frontier/network/cdx_stream.fr"),
    ("security", ["redos", "homoglyph", "signature", "zk", "adversarial", "attack"], "src/pq_signatures.rs"),
    ("maintenance", ["refactor", "warning", "dead code", "cleanup", "lint", "test coverage"], "Cargo.toml"),
    ("peerless", ["peerless", "gap", "p0", "p1", "closure", "readiness"], "scripts/close_peerless_gaps.py"),
    ("documentation", ["readme", "doc", "process_log", "audit", "report"], "docs/"),
    ("frontier_syntax", [".fr", ".frontier", "frontier run", "frontier compile", "genesis"], "frontier/core/"),
]


def _classify_text(text: str) -> list[dict]:
    lower = text.lower()
    findings = []
    for theme_id, keywords, frontier_path in THEMES:
        hits = [kw for kw in keywords if kw in lower]
        if not hits:
            continue
        priority = "P0" if theme_id in ("wasm_optimization", "codegen_depth", "self_hosting") else "P1"
        if theme_id in ("documentation", "maintenance"):
            priority = "P2"
        findings.append({
            "theme": theme_id,
            "keywords_matched": hits[:5],
            "priority": priority,
            "frontier_module": frontier_path,
            "frontier_action": _frontier_action(theme_id),
            "maintenance_action": _maintenance_action(theme_id),
        })
    return findings


def _frontier_action(theme_id: str) -> str:
    actions = {
        "wasm_optimization": "Run optimize_wasm_size.py; add frontier-slim crate or wasm-opt -Oz pipeline",
        "codegen_depth": "Extend src/wasm_codegen.rs: floats, strings, structs, imports, reassignment",
        "self_hosting": "Grow frontier/src/main.fr toward full compiler; verify with verify_self_hosting.py",
        "knowledge_engine": "Wire AlgorithmSuggestion.implementation_hint into all codegen paths",
        "swarm_optimization": "Scale swarm workers; memoize via batch_processor.py SHA3 cache",
        "runtime_gpu": "frontier run frontier/gpu/vulkan.fr --test → production Vulkan bindings",
        "runtime_ipfs": "Deploy IPFS node; wire frontier/ipfs/swarm.fr to live gateway",
        "runtime_cdx": "Connect frontier/network/cdx_stream.fr to Internet Archive CDX API",
        "security": "Run cargo test zk::; extend adversarial fuzz in syntax/wasm/",
        "maintenance": "cargo clippy --fix; remove dead_code warnings in wasm_codegen.rs",
        "peerless": "Run close_peerless_gaps.py; track in manifest/peerless_gaps.json",
        "documentation": "Regenerate docs/ARC_SYSTEM_STATUS.md and process_log.fr entries",
        "frontier_syntax": "Validate all frontier/core/*.frontier via spec_impl_bridge.py",
    }
    return actions.get(theme_id, "Review and implement in Frontier syntax")


def _maintenance_action(theme_id: str) -> str:
    actions = {
        "wasm_optimization": "Track size in manifest/wasm_size.json; CI gate on regression",
        "codegen_depth": "Add wasm_codegen unit tests per new construct",
        "self_hosting": "Bootstrap CI job: cargo run -- --bootstrap on every PR",
        "knowledge_engine": "sync_knowledge_base.py on every swarm run",
        "swarm_optimization": "Log all decisions to docs/process_log.fr (mandatory)",
        "runtime_gpu": "runtime_gpu.py health probe in deploy/health_check.sh",
        "runtime_ipfs": "runtime_ipfs.py gateway probe with 10s timeout",
        "runtime_cdx": "runtime_cdx.py CDX endpoint probe",
        "security": "Re-run scripts/test_redos.py on lexer changes",
        "maintenance": "Keep cargo test --lib green (40+ tests)",
        "peerless": "ultimate_conclusion_orchestrator.py until gaps=0",
        "documentation": "generate_arc_status.py after each merge",
        "frontier_syntax": "frontier foundation verify on release tags",
    }
    return actions.get(theme_id, "Schedule periodic review")


def analyze_shard(worker_id: int, shard: list[dict]) -> dict:
    start = time.perf_counter()
    findings: list[dict] = []
    themes_seen: dict[str, int] = {}

    for record in shard:
        text = record.get("text", "")
        if not text:
            continue
        for f in _classify_text(text):
            theme = f["theme"]
            themes_seen[theme] = themes_seen.get(theme, 0) + 1
            findings.append({
                **f,
                "source_id": record.get("id"),
                "source": record.get("source"),
                "excerpt": text[:200],
            })

    # Deduplicate by theme per worker
    unique_themes: dict[str, dict] = {}
    for f in findings:
        t = f["theme"]
        if t not in unique_themes or f["priority"] < unique_themes[t]["priority"]:
            unique_themes[t] = f

    ms = int((time.perf_counter() - start) * 1000)
    return {
        "worker_id": worker_id,
        "shard_size": len(shard),
        "findings": list(unique_themes.values()),
        "theme_counts": themes_seen,
        "records_analyzed": len(shard),
        "duration_ms": ms,
        "pass": True,
    }


def shard_corpus(records: list[dict], workers: int) -> list[list[dict]]:
    if not records:
        return [[] for _ in range(workers)]
    shards: list[list[dict]] = [[] for _ in range(workers)]
    for i, record in enumerate(records):
        shards[i % workers].append(record)
    return shards


def aggregate_findings(worker_results: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for wr in worker_results:
        for f in wr.get("findings", []):
            theme = f["theme"]
            if theme not in merged:
                merged[theme] = {**f, "worker_hits": 1, "sources": [f.get("source")]}
            else:
                merged[theme]["worker_hits"] = merged[theme].get("worker_hits", 1) + 1
                src = f.get("source")
                if src and src not in merged[theme].get("sources", []):
                    merged[theme].setdefault("sources", []).append(src)
                # Keep highest priority (P0 < P1 < P2 lexicographically for our labels)
                if f["priority"] < merged[theme]["priority"]:
                    merged[theme]["priority"] = f["priority"]

    plan = sorted(merged.values(), key=lambda x: (x["priority"], -x.get("worker_hits", 0)))
    for i, item in enumerate(plan, 1):
        item["plan_id"] = f"OPT-{i:03d}"
    return plan


def generate_report(corpus: dict, worker_results: list[dict], plan: list[dict], workers: int) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Peerless Implementation Plan",
        "",
        f"**Generated:** {now}  ",
        f"**Swarm workers:** {workers}  ",
        f"**Corpus records:** {corpus.get('record_count', 0)}  ",
        f"**Time range:** {corpus.get('time_range', {}).get('earliest', '?')} → {corpus.get('time_range', {}).get('latest', '?')}  ",
        f"**Optimization items:** {len(plan)}  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "This plan was produced by **16 Frontier swarm workers** analyzing the full account",
        "chat history corpus (decision logs, knowledge hypercube, process log, git timeline,",
        "WORKER_REPORT, gap fixes, and agent logs) from account creation through the present.",
        "",
        "Each item maps to **Frontier syntax modules**, **maintenance procedures**, and",
        "**code optimization** actions verifiable in-repo.",
        "",
        "## Optimization Plan",
        "",
        "| ID | Priority | Theme | Frontier Module | Workers |",
        "|----|----------|-------|-----------------|---------|",
    ]
    for item in plan:
        lines.append(
            f"| {item['plan_id']} | {item['priority']} | {item['theme']} | "
            f"`{item['frontier_module']}` | {item.get('worker_hits', 1)} |"
        )

    lines.extend(["", "---", "", "## Detailed Actions", ""])
    for item in plan:
        lines.extend([
            f"### {item['plan_id']}: {item['theme'].replace('_', ' ').title()}",
            "",
            f"**Priority:** {item['priority']}  ",
            f"**Frontier module:** `{item['frontier_module']}`  ",
            f"**Keywords:** {', '.join(item.get('keywords_matched', []))}  ",
            "",
            f"**Frontier action:** {item['frontier_action']}  ",
            f"**Maintenance:** {item['maintenance_action']}  ",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## Worker Shard Summary",
        "",
        "| Worker | Records | Themes | Duration |",
        "|--------|---------|--------|----------|",
    ])
    for wr in sorted(worker_results, key=lambda x: x["worker_id"]):
        lines.append(
            f"| {wr['worker_id']} | {wr['records_analyzed']} | "
            f"{len(wr.get('findings', []))} | {wr['duration_ms']}ms |"
        )

    lines.extend([
        "",
        "## Corpus Sources",
        "",
        ", ".join(f"`{s}`" for s in corpus.get("sources", [])),
        "",
        f"*Manifest: `manifest/peerless_implementation_plan.json` | Corpus: `chat_scrub/account_history_corpus.json`*",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def run_swarm(workers: int = WORKERS_DEFAULT) -> dict:
    plog = ProcessLogger(worker_id="swarm_chat_history")
    start = time.perf_counter()

    corpus = build_corpus()
    records = corpus.get("records", [])
    shards = shard_corpus(records, workers)

    plog.log("ingest", "build_corpus", "pass", {"record_count": len(records), "workers": workers})

    worker_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(analyze_shard, i + 1, shard): i + 1
            for i, shard in enumerate(shards)
        }
        for fut in as_completed(futures):
            wid = futures[fut]
            result = fut.result()
            worker_results.append(result)
            plog.log(
                f"worker_{wid}",
                "analyze_shard",
                "pass",
                {"themes": len(result.get("findings", [])), "duration_ms": result["duration_ms"]},
            )

    worker_results.sort(key=lambda x: x["worker_id"])
    plan = aggregate_findings(worker_results)
    total_ms = int((time.perf_counter() - start) * 1000)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "swarm_workers": workers,
        "corpus_records": len(records),
        "corpus_sources": corpus.get("sources", []),
        "time_range": corpus.get("time_range", {}),
        "optimization_items": len(plan),
        "duration_ms": total_ms,
        "plan": plan,
        "worker_results": [
            {
                "worker_id": w["worker_id"],
                "records_analyzed": w["records_analyzed"],
                "themes_found": len(w.get("findings", [])),
                "duration_ms": w["duration_ms"],
            }
            for w in worker_results
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generate_report(corpus, worker_results, plan, workers)

    plog.log("peerless_plan", "complete", "pass", {"items": len(plan), "duration_ms": total_ms})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="16-worker chat history swarm → Peerless plan")
    parser.add_argument("--workers", type=int, default=WORKERS_DEFAULT)
    args = parser.parse_args()
    summary = run_swarm(workers=args.workers)
    print(json.dumps({
        "pass": True,
        "workers": summary["swarm_workers"],
        "corpus_records": summary["corpus_records"],
        "optimization_items": summary["optimization_items"],
        "duration_ms": summary["duration_ms"],
        "report": str(REPORT.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
