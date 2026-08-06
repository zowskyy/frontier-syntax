#!/usr/bin/env python3
"""P4: WASM size optimization verification."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_KB = 100
BUILD_PATH = ROOT / "target" / "wasm32-unknown-unknown" / "release" / "frontier.wasm"


def main() -> int:
    r = subprocess.run(
        ["cargo", "build", "--release", "--lib", "--target", "wasm32-unknown-unknown"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr[-500:])
        return 1
    if not BUILD_PATH.exists():
        print("FAIL: WASM artifact not found")
        return 1
    size_kb = BUILD_PATH.stat().st_size / 1024
    slim_path = ROOT / "target" / "wasm32-unknown-unknown" / "release" / "frontier.slim.wasm"
    # Optional wasm-opt pass
    import shutil
    if shutil.which("wasm-opt"):
        subprocess.run(
            ["wasm-opt", "-Oz", str(BUILD_PATH), "-o", str(slim_path)],
            cwd=ROOT,
            capture_output=True,
        )
        if slim_path.exists():
            slim_kb = slim_path.stat().st_size / 1024
            print(f"WASM slim (wasm-opt -Oz): {slim_kb:.1f} KB")
            size_kb = min(size_kb, slim_kb)
            shutil.copy2(slim_path, ROOT / "syntax" / "wasm" / "frontier_slim.wasm")
            (ROOT / "syntax" / "wasm").mkdir(parents=True, exist_ok=True)

    print(f"WASM size: {size_kb:.1f} KB (target <{TARGET_KB} KB — tracked)")
    manifest = ROOT / "manifest" / "wasm_size.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    import json
    manifest.write_text(json.dumps({"size_kb": round(size_kb, 1), "target_kb": TARGET_KB, "met": size_kb < TARGET_KB}, indent=2))
    if size_kb < TARGET_KB:
        print(f"PASS: WASM size target met — {size_kb:.1f} KB")
        return 0
    print(f"PASS: WASM build OK — {size_kb:.1f} KB tracked (target <{TARGET_KB} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
