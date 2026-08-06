#!/usr/bin/env python3
"""
Ingest full account chat history from all available sources into a unified corpus.

Sources (account creation → present):
  - chat_scrub/decision_log.jsonl
  - chat_scrub/issues/*.md, gap_fixes/*.json
  - WORKER_REPORT.json (root + chat_scrub)
  - src/knowledge/hypercube/chat_knowledge.json
  - docs/process_log.fr
  - git commit messages (development timeline)
  - agent logs (self_creation, ultimate_conclusion, swarm logs)
  - cloud agent transcripts under /tmp/cursor/cloud-agent-transcripts/ (if present)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "chat_scrub" / "account_history_corpus.json"
CLOUD_TRANSCRIPTS = Path("/tmp/cursor/cloud-agent-transcripts")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_process_log(text: str) -> list[dict]:
    records = []
    for block in re.findall(r"component ProcessEntry_\w+\s*\{([^}]+)\}", text, re.DOTALL):
        entry: dict = {"source": "process_log.fr"}
        for line in block.strip().splitlines():
            line = line.strip().rstrip(",")
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            entry[key.strip()] = val.strip().strip('"')
        if entry.get("process"):
            entry["timestamp"] = entry.get("timestamp", _now())
            entry["text"] = (
                f"{entry.get('process', '')} | {entry.get('decision', '')} | "
                f"{entry.get('result', '')} | worker={entry.get('worker_id', '')}"
            )
            records.append(entry)
    return records


def _ingest_jsonl(path: Path, source: str) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        records.append({
            "id": f"{source}_{i}",
            "timestamp": obj.get("timestamp", _now()),
            "source": source,
            "text": f"{obj.get('decision', '')}: {obj.get('justification', '')}",
            "metadata": obj,
        })
    return records


def _ingest_knowledge() -> list[dict]:
    kb_path = ROOT / "src" / "knowledge" / "hypercube" / "chat_knowledge.json"
    if not kb_path.exists():
        return []
    data = json.loads(kb_path.read_text(encoding="utf-8"))
    records = []
    for e in data.get("entries", []):
        records.append({
            "id": e.get("id", ""),
            "timestamp": data.get("last_sync", data.get("updated_at", _now())),
            "source": "chat_knowledge",
            "text": f"{e.get('title', '')}: {e.get('content', '')}",
            "metadata": {
                "category": e.get("category"),
                "tags": e.get("tags", []),
                "severity": e.get("severity"),
            },
        })
    return records


def _ingest_worker_report() -> list[dict]:
    records = []
    for rel in ("WORKER_REPORT.json", "chat_scrub/WORKER_REPORT.json"):
        path = ROOT / rel
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("generated_at", _now())
        for section, key in [
            ("attack_vectors", "attack_vector"),
            ("performance_targets", "performance"),
            ("architecture_components", "architecture"),
            ("known_gaps", "gap"),
            ("resolved_gaps", "resolved_gap"),
        ]:
            for item in data.get(section, []):
                text = json.dumps(item, ensure_ascii=False)
                records.append({
                    "id": f"wr_{item.get('id', item.get('name', section))}",
                    "timestamp": ts,
                    "source": f"worker_report_{key}",
                    "text": text,
                    "metadata": {"section": section, **item},
                })
    return records


def _ingest_markdown_dir(directory: Path, source: str) -> list[dict]:
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        records.append({
            "id": f"{source}_{path.stem}",
            "timestamp": _now(),
            "source": source,
            "text": text,
            "metadata": {"file": str(path.relative_to(ROOT))},
        })
    return records


def _ingest_gap_fixes() -> list[dict]:
    fixes_dir = ROOT / "chat_scrub" / "gap_fixes"
    if not fixes_dir.exists():
        return []
    records = []
    for path in sorted(fixes_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        records.append({
            "id": f"gap_fix_{path.stem}",
            "timestamp": data.get("created_at", _now()) if isinstance(data, dict) else _now(),
            "source": "gap_fixes",
            "text": json.dumps(data, ensure_ascii=False),
            "metadata": {"file": str(path.relative_to(ROOT))},
        })
    return records


def _ingest_git_history() -> list[dict]:
    r = subprocess.run(
        ["git", "log", "--format=%H|%aI|%s", "--reverse"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return []
    records = []
    for i, line in enumerate(r.stdout.splitlines()):
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, ts, subject = parts
        records.append({
            "id": f"git_{sha[:8]}",
            "timestamp": ts,
            "source": "git_history",
            "text": subject,
            "metadata": {"sha": sha, "index": i},
        })
    return records


def _ingest_agent_logs() -> list[dict]:
    records = []
    for log_name in (
        "self_creation.log",
        "ultimate_conclusion.log",
        "swarm_gap_closure.log",
        "gap_solution.log",
    ):
        path = ROOT / log_name
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            records.append({
                "id": f"log_{log_name}_{i}",
                "timestamp": _now(),
                "source": log_name,
                "text": line.strip(),
                "metadata": {"log": log_name},
            })
    return records


def _ingest_cloud_transcripts() -> list[dict]:
    if not CLOUD_TRANSCRIPTS.exists():
        return []
    records = []
    for transcript in CLOUD_TRANSCRIPTS.rglob("transcript.json"):
        try:
            data = json.loads(transcript.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Flatten message-like content if present
        messages = data if isinstance(data, list) else data.get("messages", data.get("turns", []))
        if isinstance(messages, list):
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", msg.get("text", ""))
                    if isinstance(content, list):
                        content = " ".join(
                            c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in content
                        )
                    records.append({
                        "id": f"cloud_{transcript.parent.name}_{i}",
                        "timestamp": msg.get("timestamp", _now()),
                        "source": "cloud_agent_transcript",
                        "text": f"[{role}] {content}"[:4000],
                        "metadata": {"transcript": str(transcript)},
                    })
        else:
            records.append({
                "id": f"cloud_{transcript.parent.name}",
                "timestamp": _now(),
                "source": "cloud_agent_transcript",
                "text": json.dumps(data, ensure_ascii=False)[:4000],
                "metadata": {"transcript": str(transcript)},
            })
    return records


def build_corpus() -> dict:
    records: list[dict] = []
    records.extend(_ingest_jsonl(ROOT / "chat_scrub" / "decision_log.jsonl", "decision_log"))
    records.extend(_ingest_knowledge())
    records.extend(_ingest_worker_report())
    records.extend(_ingest_markdown_dir(ROOT / "chat_scrub" / "issues", "issues"))
    records.extend(_ingest_gap_fixes())
    pl = ROOT / "docs" / "process_log.fr"
    if pl.exists():
        records.extend(_parse_process_log(pl.read_text(encoding="utf-8")))
    records.extend(_ingest_git_history())
    records.extend(_ingest_agent_logs())
    records.extend(_ingest_cloud_transcripts())

    # Deduplicate by id
    seen: set[str] = set()
    unique: list[dict] = []
    for r in records:
        rid = r.get("id", "")
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        unique.append(r)

    unique.sort(key=lambda x: x.get("timestamp", ""))

    corpus = {
        "generated_at": _now(),
        "generator": "ingest_account_chat_history.py",
        "record_count": len(unique),
        "sources": sorted({r.get("source", "unknown") for r in unique}),
        "time_range": {
            "earliest": unique[0].get("timestamp") if unique else None,
            "latest": unique[-1].get("timestamp") if unique else None,
        },
        "records": unique,
    }
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    return corpus


def main() -> int:
    corpus = build_corpus()
    print(json.dumps({
        "pass": True,
        "record_count": corpus["record_count"],
        "sources": corpus["sources"],
        "time_range": corpus["time_range"],
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
