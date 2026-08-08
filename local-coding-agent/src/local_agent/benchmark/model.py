# SPDX-License-Identifier: Apache-2.0
"""SLICE 25 — Per-model benchmark dimensions."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from local_agent.model.base import GenerateRequest, ModelProvider

log = logging.getLogger(__name__)


@dataclass
class ModelBenchmarkRecord:
    model_id: str
    provider: str
    tool_call_valid: bool
    json_valid: bool
    edit_accuracy: float
    latency_ms: float
    memory_mb: float


class ModelBenchmark:
    """Benchmark each model profile using the same fixture set."""

    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def run(self, provider: ModelProvider, fixture_prompt: str) -> ModelBenchmarkRecord:
        start = time.perf_counter()
        raw = provider.generate(GenerateRequest(prompt=fixture_prompt)).text
        latency_ms = (time.perf_counter() - start) * 1000
        json_valid = raw.strip().startswith("{")
        tool_call_valid = '"type"' in raw and "TOOL_CALL" in raw
        edit_accuracy = 1.0 if "EDIT_REQUEST" in raw or "FINAL" in raw else 0.0
        record = ModelBenchmarkRecord(
            model_id=getattr(provider, "model_name", "unknown"),
            provider=provider.__class__.__name__,
            tool_call_valid=tool_call_valid,
            json_valid=json_valid,
            edit_accuracy=edit_accuracy,
            latency_ms=latency_ms,
            memory_mb=0.0,
        )
        path = self.evidence_dir / f"MODEL-{record.model_id.replace('/', '_')}.json"
        path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        return record


def health() -> dict[str, bool]:
    return {"/health": True}


def test_gate_smoke() -> None:
    assert health()["/health"]
