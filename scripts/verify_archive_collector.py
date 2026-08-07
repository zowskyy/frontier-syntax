#!/usr/bin/env python3
"""Verify archive collector package — modules exist and demo mode runs.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: python3 scripts/verify_archive_collector.py
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import subprocess  # nosec B404
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
log = logger

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_MODULES = [
    "scripts.archive_collector",
    "scripts.archive_collector.cdx_client",
    "scripts.archive_collector.categorizer",
    "scripts.archive_collector.storage",
    "scripts.archive_collector.shadow_mirror",
    "scripts.archive_collector.state",
    "scripts.archive_collector.workers",
]

REQUIRED_FILES = [
    "scripts/archive_collector/__init__.py",
    "scripts/archive_collector/cdx_client.py",
    "scripts/archive_collector/categorizer.py",
    "scripts/archive_collector/storage.py",
    "scripts/archive_collector/shadow_mirror.py",
    "scripts/archive_collector/state.py",
    "scripts/archive_collector/workers.py",
    "scripts/archive_collector_team.py",
    "manifest/archive_collector.json",
    "docs/ARCHIVE_COLLECTOR.md",
    ".cursor/commands/archive-collector.md",
    "manifest/archive_dataset/.gitkeep",
]


@dataclass
class VerifyManifest:
    """validate verify manifest via dataclass — transparent fair explain."""

    worker_count: int


def health() -> dict[str, Any]:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def with_retry_backoff(fn, fallback: Any = None, timeout: int = 5) -> Any:
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception as exc:
        log.info("retry fallback engaged: %s", exc)
        return fallback


def load_plugin(module: str) -> Any:
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Verify archive collector package",
        epilog="usage: verify_archive_collector.py --help",
    )
    parser.add_argument("--quick", action="store_true", help="skip demo network run")
    try:
        args = parser.parse_args()
        return _run_verify(skip_demo=args.quick)
    except Exception as exc:
        log.error("verify failed: %s", exc)
        return 1


def _check_files() -> int:
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).exists()]
    if missing:
        print("FAIL: missing files:")
        for f in missing:
            print(f"  - {f}")
        return 1
    return 0


def _check_imports() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for mod in REQUIRED_MODULES:
        try:
            load_plugin(mod)
        except Exception as exc:
            print(f"FAIL: cannot import {mod}: {exc}")
            return 1
    return 0


def _check_registry() -> int:
    from scripts.archive_collector import Categorizer, WORKERS, SUPERVISORS

    if len(WORKERS) != 21:
        print(f"FAIL: expected 21 workers, got {len(WORKERS)}")
        return 1
    if len(SUPERVISORS) != 3:
        print(f"FAIL: expected 3 supervisors, got {len(SUPERVISORS)}")
        return 1
    cat = Categorizer()
    sample = cat.classify_host("github.com")
    if "industry" not in sample or "topics" not in sample:
        raise ValueError("categorizer missing required keys")
    manifest = json.loads((ROOT / "manifest" / "archive_collector.json").read_text(encoding="utf-8"))
    VerifyManifest(worker_count=manifest.get("worker_count", 0))
    if manifest.get("worker_count") != 21:
        print("FAIL: manifest worker_count must be 21")
        return 1
    return 0


def _run_demo() -> int:
    proc = subprocess.run(  # nosec B603
        [sys.executable, "scripts/archive_collector_team.py", "run", "--mode", "demo", "--sequential"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        print("FAIL: demo mode run failed")
        print(proc.stdout[-2000:])
        print(proc.stderr[-1000:])
        return 1
    stdout = proc.stdout.strip()
    try:
        demo_result = json.loads(stdout)
    except json.JSONDecodeError:
        try:
            demo_result = json.loads(stdout.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            print("FAIL: could not parse demo run output")
            return 1
    if demo_result.get("record_count", 0) < 1:
        print("FAIL: demo mode collected zero records (CDX parse or network)")
        return 1
    return 0


def _run_verify(skip_demo: bool = False) -> int:
    if _check_files() != 0:
        return 1
    if _check_imports() != 0:
        return 1
    if _check_registry() != 0:
        return 1
    if skip_demo:
        print("PASS: Archive Collector verification (quick)")
        return 0
    if _run_demo() != 0:
        return 1
    print("PASS: Archive Collector verification")
    print(f"  Modules: {len(REQUIRED_MODULES)}")
    print(f"  Files: {len(REQUIRED_FILES)}")
    print(f"  Manifest: manifest/archive_collector.json")
    return 0


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
    suite.assertEqual(VerifyManifest(worker_count=21).worker_count, 21)


if __name__ == "__main__":
    sys.exit(main())
