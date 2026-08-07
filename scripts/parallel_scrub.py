#!/usr/bin/env python3
"""Parallel delta scrub — process multiple extraction targets concurrently."""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ["scripts/generate_chat_scrub.py", "--delta"],
    ["scripts/generate_scrub_dashboard.py"],
    ["scripts/generate_tests_from_scrub.py"],
]


def run_step(cmd: list[str]) -> dict:
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable] + [str(ROOT / cmd[0]) if not cmd[0].startswith("cargo") else cmd[0]] + cmd[1:],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    # Fix path for python scripts
    if cmd[0].endswith(".py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / cmd[0])] + cmd[1:],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    return {
        "command": cmd,
        "returncode": result.returncode,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "stdout": result.stdout[-500:] if result.stdout else "",
        "stderr": result.stderr[-300:] if result.stderr else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parallel scrub pipeline steps")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    # Step 1: primary scrub must run first (sequential)
    scrub = subprocess.run(
        [sys.executable, str(ROOT / "scripts/scrub_with_retry.py"), "--delta"],
        cwd=ROOT,
    )
    if scrub.returncode != 0:
        print("FAIL: scrub_with_retry failed")
        return 1

    # Step 2: parallel post-processing
    parallel_targets = TARGETS[1:]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_step, cmd) for cmd in parallel_targets]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    failed = [r for r in results if r["returncode"] != 0]
    for r in results:
        status = "OK" if r["returncode"] == 0 else "FAIL"
        print(f"[{status}] {r['command']} ({r['duration_ms']}ms)")

    if failed:
        return 1

    # Step 3: ingest
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "scripts/chat_knowledge_store.py"), "ingest", "--file", "chat_scrub/WORKER_REPORT.json"],
        cwd=ROOT,
    )
    print("✅ Parallel scrub complete")
    return ingest.returncode


if __name__ == "__main__":
    sys.exit(main())
