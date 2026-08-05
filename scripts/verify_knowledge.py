#!/usr/bin/env python3
"""Verify Knowledge Hypercube integration."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "src/knowledge/mod.rs",
    "src/knowledge/solver.rs",
    "src/knowledge/hypercube/mod.rs",
    "src/knowledge/hypercube/index.bin",
    "scripts/extractors/inject_knowledge.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("FAIL: Missing knowledge hypercube files:")
        for path in missing:
            print(f"  - {path}")
        return 1

    index = ROOT / "src/knowledge/hypercube/index.bin"
    if index.stat().st_size < 100:
        print("FAIL: index.bin appears empty")
        return 1

    rc = subprocess.call(["cargo", "test", "knowledge", "--lib"], cwd=ROOT)
    if rc != 0:
        print("FAIL: knowledge tests")
        return rc

    print("PASS: Knowledge Hypercube verification")
    print(f"  Index size: {index.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
