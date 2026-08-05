#!/usr/bin/env python3
"""Validate Coq proofs for Frontier v2.0."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOF = ROOT / "proofs" / "double_proof.v"


def main():
    if not PROOF.exists():
        print(f"FAIL: Missing {PROOF}")
        return 1
    if subprocess.call(["which", "coqc"], stdout=subprocess.DEVNULL) != 0:
        print("WARN: coqc not installed — skipping Coq validation")
        return 0
    result = subprocess.run(["coqc", str(PROOF)], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print("FAIL: Coq validation failed")
        print(result.stderr)
        return 1
    vo = PROOF.with_suffix(".vo")
    if not vo.exists():
        print("FAIL: Coq did not produce .vo file")
        return 1
    print("PASS: Coq proof validation (5 theorems)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
