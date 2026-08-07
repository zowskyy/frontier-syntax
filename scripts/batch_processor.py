#!/usr/bin/env python3
"""Batch processor with memoization for swarm task groups."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent


class BatchProcessor:
  def __init__(self) -> None:
      self.cache: dict[str, Any] = {}

  def hash_batch(self, batch: list[dict]) -> str:
      payload = json.dumps(batch, sort_keys=True, default=str)
      return hashlib.sha3_256(payload.encode()).hexdigest()[:16]

  def group_by_type(self, tasks: list[dict]) -> list[list[dict]]:
      groups: dict[str, list[dict]] = defaultdict(list)
      for task in tasks:
          groups[task.get("task", "default")].append(task)
      return list(groups.values())

  def process_batch(
      self,
      tasks: list[dict],
      executor: Callable[[dict], Any],
  ) -> list[Any]:
      results: list[Any] = []
      for batch in self.group_by_type(tasks):
          key = self.hash_batch(batch)
          if key in self.cache:
              results.append(self.cache[key])
              continue
          batch_results = [executor(t) for t in batch]
          result = {"batch_key": key, "results": batch_results}
          self.cache[key] = result
          results.append(result)
      return results

  def run_cmd(self, cmd: list[str], cwd: Path = ROOT) -> dict[str, Any]:
      start = time.perf_counter()
      r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
      return {
          "pass": r.returncode == 0,
          "duration_ms": int((time.perf_counter() - start) * 1000),
          "output": (r.stdout + r.stderr)[-300:],
      }
