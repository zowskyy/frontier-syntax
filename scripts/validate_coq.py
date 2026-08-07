#!/usr/bin/env python3
"""Validate all Coq proofs for Frontier v2.0."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOFS = [
    "proofs/double_proof.v",
    "proofs/constant_folding.v",
    "proofs/dead_code.v",
    "proofs/control_flow.v",
]


def main():
    missing = [p for p in PROOFS if not (ROOT / p).exists()]
    if missing:
        print("FAIL: Missing proofs:")
        for p in missing:
            print(f"  - {p}")
        return 1

    if subprocess.call(["which", "coqc"], stdout=subprocess.DEVNULL) != 0:
        print("WARN: coqc not installed — skipping Coq validation")
        return 0

    passed = 0
    for proof in PROOFS:
        result = subprocess.run(["coqc", proof], cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FAIL: {proof}")
            print(result.stderr)
            return 1
        vo = (ROOT / proof).with_suffix(".vo")
        if not vo.exists():
            print(f"FAIL: {proof} did not produce .vo")
            return 1
        passed += 1

    print(f"PASS: Coq proof validation ({passed}/{len(PROOFS)} proofs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
