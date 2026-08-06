#!/usr/bin/env python3
"""
Frontier Process Logger — async logging to docs/process_log.fr.

Every process, decision, and result is logged in Frontier-readable format
for data research and LLM training.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = ROOT / "docs" / "process_log.fr"

HEADER = """// Frontier Process Log — auto-generated, Frontier-readable
// Every process, decision, and result for data research and LLM training
version: 2.0;

module process_log;

"""


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class ProcessLogger:
    """Synchronous Frontier-readable process logger."""

    def __init__(self, log_file: Optional[Path] = None, worker_id: str = "orchestrator"):
        self.log_file = log_file or DEFAULT_LOG
        self.worker_id = worker_id
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists() or self.log_file.stat().st_size == 0:
            self.log_file.write_text(HEADER, encoding="utf-8")

    def log(
        self,
        process: str,
        decision: str,
        result: str,
        metrics: Optional[dict[str, Any]] = None,
    ) -> str:
        metrics = metrics or {}
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        entry = f"""
component ProcessEntry_{entry_id} {{
    timestamp: "{_escape(ts)}",
    process: "{_escape(process)}",
    decision: "{_escape(decision)}",
    result: "{_escape(result)}",
    worker: "{_escape(self.worker_id)}",
    duration_ms: {int(metrics.get('duration_ms', 0))},
    metrics_json: "{_escape(json.dumps(metrics, separators=(',', ':')))}",
}}
"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return entry_id


class AsyncLogger:
    """Non-blocking background writer for process_log.fr."""

    def __init__(self, log_file: Optional[Path] = None):
        self._logger = ProcessLogger(log_file=log_file, worker_id="async")
        self._queue: queue.Queue[Optional[tuple]] = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            process, decision, result, metrics, worker_id = item
            self._logger.worker_id = worker_id
            self._logger.log(process, decision, result, metrics)
            self._queue.task_done()

    def log(
        self,
        process: str,
        decision: str,
        result: str,
        metrics: Optional[dict[str, Any]] = None,
        worker_id: str = "async",
    ) -> None:
        self._queue.put((process, decision, result, metrics or {}, worker_id))

    def log_all(self, entries: list[dict[str, Any]]) -> None:
        for e in entries:
            self.log(
                e.get("process", "unknown"),
                e.get("decision", ""),
                e.get("result", ""),
                e.get("metrics"),
                e.get("worker_id", "async"),
            )

    def flush(self, timeout: float = 5.0) -> None:
        self._queue.join()
        time.sleep(min(timeout, 0.1))

    def shutdown(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=5.0)


if __name__ == "__main__":
    logger = ProcessLogger(worker_id="test")
    logger.log("self_test", "verify_format", "pass", {"duration_ms": 1})
    print(f"✅ Logged to {DEFAULT_LOG.relative_to(ROOT)}")
