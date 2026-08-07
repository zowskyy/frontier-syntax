#!/usr/bin/env python3
"""
Canonical WASM size measurement — single source of truth for issue #48.

Builds the wasm-slim release library (default browser compiler surface),
optionally runs wasm-opt -Oz, and writes manifest/wasm_size.json.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_KB = 100
ARTIFACT_DIR = ROOT / "target" / "wasm32-unknown-unknown" / "release"
RAW_ARTIFACT = ARTIFACT_DIR / "frontier.wasm"
OPT_ARTIFACT = ARTIFACT_DIR / "frontier.opt.wasm"
MANIFEST = ROOT / "manifest" / "wasm_size.json"

BUILD_CMD = [
    "cargo", "build", "--release", "--lib",
    "--target", "wasm32-unknown-unknown",
    "--no-default-features",
    "--features", "wasm-slim",
]


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def find_wasm_opt() -> str | None:
    for candidate in (
        os.environ.get("WASMOPT"),
        shutil.which("wasm-opt"),
        "/tmp/binaryen-version_122/bin/wasm-opt",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def optimize_wasm(raw: Path, out: Path) -> bool:
    wasm_opt = find_wasm_opt()
    if not wasm_opt:
        return False
    r = subprocess.run(
        [wasm_opt, "-Oz", "--converge", "--enable-bulk-memory", "--strip-debug", "--strip-producers", "--flatten", str(raw), "-o", str(out)],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and out.exists()


def measure() -> dict:
    r = subprocess.run(BUILD_CMD, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return {"pass": False, "error": (r.stderr + r.stdout)[-600:]}

    if not RAW_ARTIFACT.exists():
        return {"pass": False, "error": f"artifact missing: {RAW_ARTIFACT}"}

    raw_bytes = RAW_ARTIFACT.stat().st_size
    optimized = optimize_wasm(RAW_ARTIFACT, OPT_ARTIFACT)
    measured_path = OPT_ARTIFACT if optimized else RAW_ARTIFACT
    size_bytes = measured_path.stat().st_size
    size_kb = round(size_bytes / 1024, 1)

    result = {
        "measured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "measurement_script": "scripts/measure_wasm_size.py",
        "build_command": " ".join(BUILD_CMD),
        "build_profile": "wasm-slim",
        "artifact_path": str(measured_path.relative_to(ROOT)),
        "raw_artifact_path": str(RAW_ARTIFACT.relative_to(ROOT)),
        "raw_size_bytes": raw_bytes,
        "raw_size_kb": round(raw_bytes / 1024, 1),
        "wasm_opt_applied": optimized,
        "size_bytes": size_bytes,
        "size_kb": size_kb,
        "target_kb": TARGET_KB,
        "met": size_kb < TARGET_KB,
        "git_sha": git_sha(),
        "note": (
            "wasm-slim build: parser + codegen + compile_frontier_wasm export. "
            "Full browser API (BrowserCompiler) requires --features full. "
            "Baseline monolithic build was ~885 KB; slim + wasm-opt is measured here."
        ),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"pass": True, **result}


def main() -> int:
    result = measure()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
