#!/usr/bin/env python3
"""Command entry: ingest account chat history + 16-worker Peerless plan generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    workers = 16
    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        if idx + 1 < len(sys.argv):
            workers = int(sys.argv[idx + 1])

    steps = [
        ("ingest", [sys.executable, str(ROOT / "scripts" / "ingest_account_chat_history.py")]),
        ("analyze", [sys.executable, str(ROOT / "scripts" / "swarm_chat_history_analyzer.py"), "--workers", str(workers)]),
        ("sync_kb", [sys.executable, str(ROOT / "scripts" / "sync_knowledge_base.py")]),
    ]
    results = []
    for name, cmd in steps:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        results.append({"step": name, "pass": r.returncode == 0, "output": (r.stdout + r.stderr)[-300:]})

    manifest = ROOT / "manifest" / "peerless_implementation_plan.json"
    plan_count = 0
    if manifest.exists():
        plan_count = json.loads(manifest.read_text()).get("optimization_items", 0)

    summary = {
        "pass": all(s["pass"] for s in results),
        "workers": workers,
        "optimization_items": plan_count,
        "steps": results,
        "report": "audit_reports/peerless_implementation_plan.md",
        "manifest": "manifest/peerless_implementation_plan.json",
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
