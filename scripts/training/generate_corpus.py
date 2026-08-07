#!/usr/bin/env python3
"""Generate deterministic Frontier training corpus samples (Phase 6 Slice 6.1)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "manifest" / "training_corpus"
JSONL = OUT_DIR / "frontier_v1.jsonl"
STATS = OUT_DIR / "stats.json"
MIN_SAMPLES = 1000


def git_sha() -> str:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"


def sample_id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:04d}"


def build_samples(count: int) -> list[dict]:
    sha = git_sha()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    samples: list[dict] = []

    # const return — 400 samples
    for n in range(min(400, count)):
        completion = f"fn main(): int {{ return {n}; }}"
        samples.append(
            {
                "id": sample_id("const", n),
                "prompt": f"Write Frontier main returning {n}",
                "completion": completion,
                "expected_return": n,
                "features": ["const_return"],
                "source_spec": "verify_wasm_codegen.py#const_return",
                "compiler_git_sha": sha,
                "generated_at": now,
            }
        )

    # let binding — 300 samples
    for n in range(min(300, max(0, count - len(samples)))):
        completion = f"fn main(): int {{ let x: int = {n}; return x; }}"
        samples.append(
            {
                "id": sample_id("let", n),
                "prompt": f"Write Frontier main with let x = {n}",
                "completion": completion,
                "expected_return": n,
                "features": ["let"],
                "source_spec": "feature_matrix#bindings",
                "compiler_git_sha": sha,
                "generated_at": now,
            }
        )

    # if/else — 200 samples
    for n in range(min(200, max(0, count - len(samples)))):
        threshold = n % 50
        completion = (
            f"fn main(): int {{\n"
            f"    let x: int = {n};\n"
            f"    if (x > {threshold}) {{\n"
            f"        return x;\n"
            f"    }}\n"
            f"    return 0;\n"
            f"}}"
        )
        expected = n if n > threshold else 0
        samples.append(
            {
                "id": sample_id("if", n),
                "prompt": f"Write Frontier main with if x > {threshold}",
                "completion": completion,
                "expected_return": expected,
                "features": ["let", "if"],
                "source_spec": "feature_matrix#control_flow",
                "compiler_git_sha": sha,
                "generated_at": now,
            }
        )

    # function call — 100 samples
    for n in range(min(100, max(0, count - len(samples)))):
        completion = (
            f"fn double(x: int): int {{\n"
            f"    return x * 2;\n"
            f"}}\n"
            f"fn main(): int {{\n"
            f"    return double({n});\n"
            f"}}"
        )
        samples.append(
            {
                "id": sample_id("call", n),
                "prompt": f"Write Frontier main calling double({n})",
                "completion": completion,
                "expected_return": n * 2,
                "features": ["call"],
                "source_spec": "verify_wasm_codegen.py#function_call",
                "compiler_git_sha": sha,
                "generated_at": now,
            }
        )

    idx = 0
    while len(samples) < count:
        n = idx
        completion = f"fn main(): int {{ return {1000 + n}; }}"
        samples.append(
            {
                "id": sample_id("pad", n),
                "prompt": f"Write Frontier main returning {1000 + n}",
                "completion": completion,
                "expected_return": 1000 + n,
                "features": ["const_return"],
                "source_spec": "padding",
                "compiler_git_sha": sha,
                "generated_at": now,
            }
        )
        idx += 1

    return samples[:count]


def write_corpus(samples: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with JSONL.open("w", encoding="utf-8") as f:
        for row in samples:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    digest = hashlib.sha256(JSONL.read_bytes()).hexdigest()
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/training/generate_corpus.py",
        "sample_count": len(samples),
        "jsonl_sha256": digest,
        "compiler_git_sha": samples[0]["compiler_git_sha"] if samples else "unknown",
        "feature_tags": sorted({tag for s in samples for tag in s.get("features", [])}),
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Frontier training corpus")
    parser.add_argument("--count", type=int, default=MIN_SAMPLES, help="Number of samples")
    args = parser.parse_args()

    samples = build_samples(max(args.count, MIN_SAMPLES))
    write_corpus(samples)
    print(json.dumps({"pass": True, "samples": len(samples), "jsonl": str(JSONL.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
