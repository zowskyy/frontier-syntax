#!/usr/bin/env python3
"""
Swarm KB Optimizer — parallel workers enrich the Frontier knowledge hypercube.

Workers run concurrently:
  1. process_log ingest (full history)
  2. core .frontier spec summaries
  3. audit report indexing
  4. optimization manifest sync
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from process_logger import ProcessLogger  # noqa: E402

KNOWLEDGE = ROOT / "src" / "knowledge" / "hypercube" / "chat_knowledge.json"
PROCESS_LOG = ROOT / "docs" / "process_log.fr"
MANIFEST = ROOT / "manifest" / "swarm_kb_optimizer.json"
REPORT = ROOT / "audit_reports" / "swarm_kb_optimizer_report.md"


def _load_knowledge() -> dict:
    return json.loads(KNOWLEDGE.read_text(encoding="utf-8"))


def _save_knowledge(data: dict) -> None:
    data["entry_count"] = len(data.get("entries", []))
    data["last_sync"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    KNOWLEDGE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_process_entries(text: str) -> list[dict]:
    entries = []
    for block in re.findall(r"component ProcessEntry_\w+\s*\{([^}]+)\}", text, re.DOTALL):
        entry = {}
        for line in block.strip().splitlines():
            line = line.strip().rstrip(",")
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            entry[key.strip()] = val.strip().strip('"')
        if entry.get("process"):
            entries.append(entry)
    return entries


def worker_process_log() -> dict:
    start = time.perf_counter()
    if not PROCESS_LOG.exists():
        return {"worker": "process_log", "pass": False, "added": 0}
    data = _load_knowledge()
    entries = data.get("entries", [])
    existing = {e.get("id") for e in entries}
    added = 0
    for i, le in enumerate(_parse_process_entries(PROCESS_LOG.read_text(encoding="utf-8"))):
        eid = f"swarm_process_{le.get('process', 'x')}_{le.get('timestamp', i)}"
        if eid in existing:
            continue
        entries.append({
            "id": eid,
            "category": "swarm_optimization",
            "title": f"Swarm: {le.get('process', 'unknown')}",
            "content": (
                f"Decision: {le.get('decision', '')}. "
                f"Result: {le.get('result', '')}. "
                f"Worker: {le.get('worker_id', '')}."
            ),
            "tags": ["swarm", "process_log", "llm_training", "optimization"],
            "severity": "info",
            "source": "docs/process_log.fr",
        })
        added += 1
    data["entries"] = entries
    _save_knowledge(data)
    ms = int((time.perf_counter() - start) * 1000)
    return {"worker": "process_log", "pass": True, "added": added, "duration_ms": ms}


def worker_core_specs() -> dict:
    start = time.perf_counter()
    core_dir = ROOT / "frontier" / "core"
    data = _load_knowledge()
    entries = data.get("entries", [])
    existing = {e.get("id") for e in entries}
    added = 0
    for spec in sorted(core_dir.glob("*.frontier")):
        eid = f"core_spec_{spec.stem}"
        if eid in existing:
            continue
        text = spec.read_text(encoding="utf-8", errors="replace")
        summary = text[:400].replace("\n", " ").strip()
        entries.append({
            "id": eid,
            "category": "language_spec",
            "title": f"Core module: {spec.stem}",
            "content": summary,
            "tags": ["frontier", "core", "spec", "language"],
            "severity": "info",
            "source": str(spec.relative_to(ROOT)),
        })
        added += 1
    data["entries"] = entries
    _save_knowledge(data)
    ms = int((time.perf_counter() - start) * 1000)
    return {"worker": "core_specs", "pass": True, "added": added, "duration_ms": ms}


def worker_audit_reports() -> dict:
    start = time.perf_counter()
    audit_dir = ROOT / "audit_reports"
    data = _load_knowledge()
    entries = data.get("entries", [])
    existing = {e.get("id") for e in entries}
    added = 0
    for report in sorted(audit_dir.glob("*.md")):
        eid = f"audit_{report.stem}"
        if eid in existing:
            continue
        lines = report.read_text(encoding="utf-8", errors="replace").splitlines()
        title = next((l.lstrip("# ").strip() for l in lines if l.startswith("#")), report.stem)
        entries.append({
            "id": eid,
            "category": "audit",
            "title": title,
            "content": "\n".join(lines[:15]),
            "tags": ["audit", "swarm", "verification"],
            "severity": "info",
            "source": str(report.relative_to(ROOT)),
        })
        added += 1
    data["entries"] = entries
    _save_knowledge(data)
    ms = int((time.perf_counter() - start) * 1000)
    return {"worker": "audit_reports", "pass": True, "added": added, "duration_ms": ms}


def worker_optimization_manifests() -> dict:
    start = time.perf_counter()
    data = _load_knowledge()
    entries = data.get("entries", [])
    existing = {e.get("id") for e in entries}
    added = 0
    for mf in sorted((ROOT / "manifest").glob("*.json")):
        eid = f"manifest_{mf.stem}"
        if eid in existing:
            continue
        try:
            manifest = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries.append({
            "id": eid,
            "category": "manifest",
            "title": f"Manifest: {mf.stem}",
            "content": json.dumps(manifest, indent=0)[:800],
            "tags": ["manifest", "optimization", "swarm"],
            "severity": "info",
            "source": str(mf.relative_to(ROOT)),
        })
        added += 1
    data["entries"] = entries
    _save_knowledge(data)
    ms = int((time.perf_counter() - start) * 1000)
    return {"worker": "optimization_manifests", "pass": True, "added": added, "duration_ms": ms}


WORKERS = [
    worker_process_log,
    worker_core_specs,
    worker_audit_reports,
    worker_optimization_manifests,
]


def main() -> int:
    plog = ProcessLogger(worker_id="swarm_kb_optimizer")
    start = time.perf_counter()
    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in WORKERS}
        for fut in as_completed(futures):
            result = fut.result()
            results.append(result)
            plog.log(
                result["worker"],
                "kb_ingest",
                "pass" if result.get("pass") else "fail",
                {"added": result.get("added", 0), "duration_ms": result.get("duration_ms", 0)},
            )

    # Run standard sync for dedupe / metadata
    subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_knowledge_base.py")], cwd=ROOT, capture_output=True)

    final = _load_knowledge()
    total_ms = int((time.perf_counter() - start) * 1000)
    total_added = sum(r.get("added", 0) for r in results)
    summary = {
        "workers": len(WORKERS),
        "total_added": total_added,
        "knowledge_entries": final.get("entry_count", len(final.get("entries", []))),
        "duration_ms": total_ms,
        "worker_results": results,
        "all_pass": all(r.get("pass") for r in results),
    }
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"# Swarm KB Optimizer Report\n\n**Generated:** {now}\n\n"
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Knowledge entries | {summary['knowledge_entries']} |\n"
        f"| New entries added | {total_added} |\n"
        f"| Duration | {total_ms}ms |\n\n"
        + "\n".join(
            f"- **{r['worker']}**: +{r.get('added', 0)} entries ({r.get('duration_ms', 0)}ms)"
            for r in results
        ),
        encoding="utf-8",
    )
    plog.log("swarm_kb_optimizer", "complete", "pass", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
