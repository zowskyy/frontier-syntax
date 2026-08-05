#!/usr/bin/env python3
"""Run all Frontier verification scripts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = [
    "build/arc_orchestrator.py --verify",
    "scripts/verify_cycle1.py",
    "scripts/verify_language_hardening.py",
    "scripts/verify_v2.py",
    "scripts/validate_coq.py",
    "scripts/verify_knowledge.py",
]


def main() -> int:
    failed = []
    for script in SCRIPTS:
        parts = script.split()
        cmd = [sys.executable, str(ROOT / parts[0])] + parts[1:] if parts[0].endswith(".py") else [sys.executable, str(ROOT / parts[0])] + parts[1:]
        if parts[0] == "build/arc_orchestrator.py":
            cmd = [sys.executable, str(ROOT / "build" / "arc_orchestrator.py"), "--verify"]
        else:
            cmd = [sys.executable, str(ROOT / parts[0])]
        print(f"\n=== Running {script} ===")
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc != 0:
            failed.append(script)

    if failed:
        print("\nFAIL:", ", ".join(failed))
        return 1

    print("\n✅ All verification scripts passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
