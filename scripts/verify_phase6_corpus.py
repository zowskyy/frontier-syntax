#!/usr/bin/env python3
"""Phase 6 gate wrapper — corpus generation + validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATE = ROOT / "scripts" / "training" / "validate_corpus.py"


def main() -> int:
    r = subprocess.run([sys.executable, str(VALIDATE)], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        return r.returncode
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return 1
    if data.get("pass"):
        print("PASS: Phase 6 training corpus gate")
    return 0 if data.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
