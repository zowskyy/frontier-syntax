#!/usr/bin/env python3
"""Validate full training corpus shard (Phase 6 Slice 6.1 gate)."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "manifest" / "training_corpus"
JSONL = CORPUS_DIR / "frontier_v1.jsonl"
STATS = CORPUS_DIR / "stats.json"
MANIFEST = ROOT / "manifest" / "phase6_corpus_verify.json"
MIN_SAMPLES = 1000
VALIDATE_SAMPLE = ROOT / "scripts" / "training" / "validate_sample.py"
GENERATE = ROOT / "scripts" / "training" / "generate_corpus.py"


def load_samples() -> list[dict]:
    if not JSONL.exists():
        return []
    rows = []
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def ensure_corpus() -> None:
    if JSONL.exists():
        samples = load_samples()
        if len(samples) >= MIN_SAMPLES:
            return
    subprocess.run([sys.executable, str(GENERATE), "--count", str(MIN_SAMPLES)], cwd=ROOT, check=False)


def validate_samples(samples: list[dict], *, full: bool, seed: int = 42) -> dict:
    compile_pass = 0
    wasmtime_pass = 0
    failures: list[dict] = []

    if full:
        subset = samples
    else:
        random.seed(seed)
        subset = random.sample(samples, min(50, len(samples)))

    for sample in subset:
        r = subprocess.run(
            [sys.executable, str(VALIDATE_SAMPLE), "--json", json.dumps(sample)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        try:
            row = json.loads(r.stdout)
        except json.JSONDecodeError:
            row = {"pass": False, "compile_pass": False, "wasmtime_pass": False}
        if row.get("compile_pass"):
            compile_pass += 1
        if row.get("wasmtime_pass"):
            wasmtime_pass += 1
        if not row.get("pass"):
            failures.append({"id": sample.get("id"), "output": (r.stdout + r.stderr)[-200:]})

    compile_rate = compile_pass / len(subset) if subset else 0.0
    wasmtime_rate = wasmtime_pass / len(subset) if subset else 0.0
    return {
        "validated_count": len(subset),
        "total_samples": len(samples),
        "compile_pass_rate": compile_rate,
        "wasmtime_pass_rate": wasmtime_rate,
        "failures": failures[:10],
        "full_validation": full,
    }


def verify(*, full: bool = False) -> dict:
    ensure_corpus()
    samples = load_samples()
    count_ok = len(samples) >= MIN_SAMPLES
    validation = validate_samples(samples, full=full) if samples else {}

    compile_ok = validation.get("compile_pass_rate", 0) >= 1.0 if validation else False
    wasmtime_ok = validation.get("wasmtime_pass_rate", 0) >= 0.95 if validation else False
    if not full and validation:
        # spot-check mode: require 100% on sample
        compile_ok = validation.get("compile_pass_rate", 0) >= 1.0
        wasmtime_ok = validation.get("wasmtime_pass_rate", 0) >= 0.95

    result = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/training/validate_corpus.py",
        "sample_count": len(samples),
        "min_samples": MIN_SAMPLES,
        "count_ok": count_ok,
        "validation": validation,
        "pass": count_ok and compile_ok and wasmtime_ok and len(validation.get("failures", [])) == 0,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if STATS.exists() and result["pass"]:
        stats = json.loads(STATS.read_text(encoding="utf-8"))
        stats["validated_at"] = result["verified_at"]
        stats["validation_pass"] = True
        stats["wasmtime_pass_rate"] = validation.get("wasmtime_pass_rate")
        STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate training corpus")
    parser.add_argument("--full", action="store_true", help="Validate every sample (slow)")
    args = parser.parse_args()
    result = verify(full=args.full)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
