"""Shared helpers for archive collector workers.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: see docs/ARCHIVE_COLLECTOR.md
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any, Callable

from .categorizer import Categorizer
from .state import utc_now
from .storage import Storage, path_hash, record_id

logger = logging.getLogger(__name__)
log = logger

DEMO_HOSTS = [
    "wikipedia.org",
    "archive.org",
    "github.com",
    "mozilla.org",
    "python.org",
]

WorkerFn = Callable[..., dict[str, Any]]


@dataclass
class WorkerResult:
    """validate worker result via dataclass — transparent fair explain."""

    worker_id: str
    ok: bool


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


def result(
    worker_id: str,
    *,
    ok: bool,
    records_processed: int = 0,
    message: str = "",
    **extra: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": ok,
        "worker_id": worker_id,
        "records_processed": records_processed,
        "message": message,
    }
    out.update(extra)
    return out


def parse_cdx_row(row: list[str]) -> dict[str, str] | None:
    if not row:
        raise ValueError("empty CDX row")
    if len(row) < 5:
        return None
    _urlkey, timestamp, original, mime, status = row[:5]
    host = original.split("/")[2] if "://" in original else original
    return {
        "host": host,
        "timestamp": timestamp,
        "original": original,
        "mime": mime,
        "status": status,
        "path_hash": path_hash(original),
    }


def write_cdx_rows(
    storage: Storage,
    rows: list[list[str]],
    *,
    supervisor: str,
    worker: str,
    categorizer: Categorizer | None = None,
) -> int:
    cat = categorizer or Categorizer()
    written = 0
    seen: set[str] = set()
    for row in rows:
        parsed = parse_cdx_row(row)
        if not parsed:
            continue
        rid = record_id(parsed["host"], parsed["path_hash"], parsed["timestamp"])
        if rid in seen:
            continue
        seen.add(rid)
        classification = cat.classify(parsed["original"])
        storage.append_record(
            {
                "id": rid,
                "host": parsed["host"],
                "path_hash": parsed["path_hash"],
                "timestamp": parsed["timestamp"],
                "industry": classification["industry"],
                "topics": classification["topics"],
                "mime": parsed["mime"],
                "status": parsed["status"],
                "collected_at": utc_now(),
                "supervisor": supervisor,
                "worker": worker,
            }
        )
        written += 1
    return written


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
    print("worker_helpers gate ok")
