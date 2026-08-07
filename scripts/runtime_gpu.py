#!/usr/bin/env python3
"""P1: Live GPU runtime verification."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "frontier" / "gpu" / "vulkan.fr"


def main() -> int:
    if not MODULE.exists():
        print(f"FAIL: {MODULE} missing")
        return 1
    r = subprocess.run(
        ["cargo", "run", "--quiet", "--bin", "frontier", "--", "run", str(MODULE), "--test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return 1
    print("PASS: Live GPU runtime (vulkan.fr compile + test)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
