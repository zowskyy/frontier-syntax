#!/usr/bin/env python3
"""
Canonical WASM size measurement — single source of truth for issue #48.

Always measures the same artifact with the same build flags.
Writes manifest/wasm_size.json (authoritative).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_KB = 100
# Authoritative artifact: release lib WASM (same path optimize_wasm_size.py uses)
ARTIFACT = ROOT / "target" / "wasm32-unknown-unknown" / "release" / "frontier.wasm"
MANIFEST = ROOT / "manifest" / "wasm_size.json"

BUILD_CMD = [
    "cargo", "build", "--release", "--lib",
    "--target", "wasm32-unknown-unknown",
]


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def measure() -> dict:
    r = subprocess.run(BUILD_CMD, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return {"pass": False, "error": r.stderr[-400:]}

    if not ARTIFACT.exists():
        return {"pass": False, "error": f"artifact missing: {ARTIFACT}"}

    size_bytes = ARTIFACT.stat().st_size
    size_kb = round(size_bytes / 1024, 1)

    result = {
        "measured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "measurement_script": "scripts/measure_wasm_size.py",
        "build_command": " ".join(BUILD_CMD),
        "artifact_path": str(ARTIFACT.relative_to(ROOT)),
        "size_bytes": size_bytes,
        "size_kb": size_kb,
        "target_kb": TARGET_KB,
        "met": size_kb < TARGET_KB,
        "git_sha": git_sha(),
        "note": (
            "Historical issue titles cite ~760 KB from an earlier build profile. "
            "This manifest is the only authoritative number — do not cite README or issue text."
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
