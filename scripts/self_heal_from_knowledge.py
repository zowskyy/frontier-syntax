#!/usr/bin/env python3
"""Knowledge-driven self-heal — retry failed scrub/verify steps using gap knowledge."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from chat_knowledge_store import query_knowledge  # noqa: E402

HEAL_STEPS = [
    [sys.executable, str(ROOT / "scripts/scrub_with_retry.py"), "--max-retries", "3"],
    [sys.executable, str(ROOT / "scripts/chat_knowledge_store.py"), "ingest", "--file", "chat_scrub/WORKER_REPORT.json"],
    ["cargo", "test", "--lib"],
    [sys.executable, str(ROOT / "scripts/generate_tests_from_scrub.py"), "--run"],
]


def heal_step(cmd: list[str], context: str) -> bool:
    print(f"Healing: {' '.join(cmd)}")
    hints = query_knowledge(context, limit=3)
    if hints:
        print(f"  Knowledge hints: {[h.get('title', '') for h in hints]}")

    for attempt in range(1, 4):
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ OK (attempt {attempt})")
            return True
        delay = 2 ** attempt
        print(f"  ⚠️ Failed (attempt {attempt}), retry in {delay}s")
        if result.stderr:
            print(f"  {result.stderr[-200:]}")
        time.sleep(delay)
    return False


def main() -> int:
    log_path = ROOT / "chat_scrub" / "self_heal.log"
    failures = []

    for cmd in HEAL_STEPS:
        context = cmd[1] if len(cmd) > 1 else "verification"
        if isinstance(context, str) and "/" in context:
            context = Path(context).stem
        if not heal_step(cmd, context):
            failures.append(cmd)

    status = {
        "healed": len(HEAL_STEPS) - len(failures),
        "failed": len(failures),
        "failures": [str(c) for c in failures],
    }
    log_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    if failures:
        print(f"❌ Self-heal partial: {status['healed']}/{len(HEAL_STEPS)} steps OK")
        return 1
    print("✅ Self-heal complete — all steps recovered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
