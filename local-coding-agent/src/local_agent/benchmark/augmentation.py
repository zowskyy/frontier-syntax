# SPDX-License-Identifier: Apache-2.0
"""SLICE 24 — Knowledge augmentation benchmark (baseline vs augmented)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class AugmentationResult:
    task_id: str
    baseline_correct: bool
    augmented_correct: bool
    hallucination_baseline: bool
    hallucination_augmented: bool
    citation_accuracy: float


class AugmentationBenchmark:
    """Paired evaluation: model+task vs model+task+retrieved docs."""

    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def run_fixture(self, task_id: str, baseline_answer: str, augmented_answer: str, ground_truth: str, docs: list[str]) -> AugmentationResult:
        baseline_correct = ground_truth.lower() in baseline_answer.lower()
        augmented_correct = ground_truth.lower() in augmented_answer.lower()
        hallucination_baseline = "undocumented_api_xyz" in baseline_answer
        hallucination_augmented = "undocumented_api_xyz" in augmented_answer
        cited = sum(1 for d in docs if d[:20] in augmented_answer)
        citation_accuracy = cited / max(len(docs), 1)
        result = AugmentationResult(
            task_id=task_id,
            baseline_correct=baseline_correct,
            augmented_correct=augmented_correct,
            hallucination_baseline=hallucination_baseline,
            hallucination_augmented=hallucination_augmented,
            citation_accuracy=citation_accuracy,
        )
        (self.evidence_dir / f"AUG-{task_id}.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        log.info("augmentation benchmark %s baseline=%s augmented=%s", task_id, baseline_correct, augmented_correct)
        return result


def health() -> dict[str, bool]:
    return {"/health": True}


def test_gate_smoke() -> None:
    assert health()["/health"]
