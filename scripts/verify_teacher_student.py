#!/usr/bin/env python3
"""P6: Teacher-student unity module verification."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "frontier" / "learning" / "teacher_student.fr"


def main() -> int:
    if not MODULE.exists():
        print(f"FAIL: {MODULE} missing")
        return 1
    r = subprocess.run(
        ["cargo", "run", "--quiet", "--bin", "frontier", "--", "parse", str(MODULE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return 1
    content = MODULE.read_text(encoding="utf-8")
    required = ["Teacher", "Student", "exchange_knowledge", "symbiotic"]
    missing = [k for k in required if k not in content]
    if missing:
        print(f"FAIL: missing symbols: {missing}")
        return 1
    print("PASS: Teacher-student unity module")
    return 0


if __name__ == "__main__":
    sys.exit(main())
