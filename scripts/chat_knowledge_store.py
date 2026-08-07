#!/usr/bin/env python3
"""Shared chat knowledge index for scrub ingest and semantic query."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "src" / "knowledge" / "hypercube" / "chat_knowledge.json"
METRICS_FILE = ROOT / "chat_scrub" / "metrics.json"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _tfidf_score(query_tokens: list[str], doc_tokens: list[str], doc_count: int, df: Counter) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    tf = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        if token not in tf:
            continue
        idf = math.log((doc_count + 1) / (df[token] + 1)) + 1.0
        score += (tf[token] / len(doc_tokens)) * idf
    return score


def report_to_entries(report: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for vector in report.get("attack_vectors", []):
        entries.append(
            {
                "id": vector.get("id", ""),
                "category": "attack_vector",
                "title": vector.get("name", ""),
                "content": f"{vector.get('description', '')} Mitigation: {vector.get('mitigation', '')}",
                "severity": vector.get("severity", "medium"),
                "tags": ["security", vector.get("status", "")],
                "source": vector.get("code", ""),
            }
        )

    for gap in report.get("known_gaps", []):
        entries.append(
            {
                "id": gap.get("id", ""),
                "category": "gap",
                "title": gap.get("description", ""),
                "content": gap.get("description", ""),
                "severity": gap.get("priority", "P2"),
                "tags": ["gap", gap.get("priority", "")],
                "source": gap.get("file") or "",
            }
        )

    for component in report.get("architecture_components", []):
        entries.append(
            {
                "id": f"arch_{component.get('name', '').lower().replace(' ', '_')}",
                "category": "architecture",
                "title": component.get("name", ""),
                "content": f"Status: {component.get('status', '')}. Path: {component.get('path', '')}",
                "severity": component.get("status", ""),
                "tags": ["architecture"],
                "source": component.get("path", ""),
            }
        )

    for target in report.get("performance_targets", []):
        entries.append(
            {
                "id": target.get("id", ""),
                "category": "performance",
                "title": target.get("metric", ""),
                "content": f"Current: {target.get('current', '')}. Target: {target.get('target', '')}. Plan: {target.get('plan_10x', '')}",
                "severity": target.get("priority", "P2"),
                "tags": ["performance", "10x"],
                "source": target.get("file", "") if "file" in target else "",
            }
        )

    for cmd in report.get("cli_commands", []):
        entries.append(
            {
                "id": f"cli_{hash(cmd.get('command', '')) & 0xFFFF:x}",
                "category": "cli",
                "title": cmd.get("command", ""),
                "content": cmd.get("purpose", ""),
                "severity": "info",
                "tags": ["cli"],
                "source": cmd.get("command", ""),
            }
        )

    return entries


def ingest_report(report_path: Path, index_path: Path = DEFAULT_INDEX) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    entries = report_to_entries(report)
    existing: dict[str, Any] = {"version": 1, "entries": [], "ingested_at": []}
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))

    known_ids = {e["id"] for e in existing.get("entries", [])}
    new_entries = [e for e in entries if e["id"] and e["id"] not in known_ids]
    merged = existing.get("entries", []) + new_entries

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "version": 1,
        "updated_at": now,
        "source_report": str(report_path.relative_to(ROOT)),
        "entry_count": len(merged),
        "entries": merged,
        "ingested_at": existing.get("ingested_at", []) + [now],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "new_entries": len(new_entries),
        "total_entries": len(merged),
        "index_path": str(index_path.relative_to(ROOT)),
    }


def query_knowledge(query: str, index_path: Path = DEFAULT_INDEX, limit: int = 10) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []

    data = json.loads(index_path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not entries:
        return []

    query_tokens = _tokenize(query)
    df: Counter = Counter()
    doc_tokens_list: list[list[str]] = []
    for entry in entries:
        text = f"{entry.get('title', '')} {entry.get('content', '')} {' '.join(entry.get('tags', []))}"
        tokens = _tokenize(text)
        doc_tokens_list.append(tokens)
        for token in set(tokens):
            df[token] += 1

    scored: list[tuple[float, dict[str, Any]]] = []
    for entry, tokens in zip(entries, doc_tokens_list):
        score = _tfidf_score(query_tokens, tokens, len(entries), df)
        if score > 0:
            scored.append((score, {**entry, "score": round(score, 4)}))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def record_metrics(metrics: dict[str, Any]) -> None:
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, Any]] = []
    if METRICS_FILE.exists():
        history = json.loads(METRICS_FILE.read_text(encoding="utf-8")).get("history", [])
    history.append(metrics)
    METRICS_FILE.write_text(json.dumps({"history": history[-365:]}, indent=2), encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Chat knowledge store CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("--file", required=True, help="WORKER_REPORT.json path")

    query_parser = sub.add_parser("query")
    query_parser.add_argument("text", help="Search query")
    query_parser.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    if args.command == "ingest":
        result = ingest_report(ROOT / args.file)
        print(json.dumps(result))
        return 0
    if args.command == "query":
        results = query_knowledge(args.text, limit=args.limit)
        print(json.dumps(results, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
