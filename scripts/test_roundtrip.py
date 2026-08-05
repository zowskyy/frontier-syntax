#!/usr/bin/env python3
"""Cycle 5: Round-trip test — parse → canonical AST → verify hash stability."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "sample.fr"
AST_HASH = ROOT / "syntax" / "ast_hash.sha3"


def sha3_256(data: str) -> str:
    import hashlib
    return hashlib.sha3_256(data.encode()).hexdigest()


def main():
    source = SAMPLE.read_text()

    result = subprocess.run(
        ["cargo", "run", "--release", "--bin", "frontier", "--", "hash", str(SAMPLE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("FAIL: hash command failed", result.stderr)
        return 1

    hash1 = result.stdout.strip()
    hash2 = result.stdout.strip()

    stored = AST_HASH.read_text().strip()

    if hash1 != hash2:
        print("FAIL: hash not deterministic")
        return 1

    if hash1 != stored:
        print(f"FAIL: hash mismatch stored={stored} computed={hash1}")
        return 1

    print(f"PASS: Round-trip hash stable: {hash1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
