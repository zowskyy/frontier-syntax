#!/usr/bin/env python3
"""Continuous scrub daemon — runs delta scrub on interval."""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERVAL = 3600

def main() -> None:
    while True:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "scrub_with_retry.py"), "--delta"],
            cwd=ROOT,
        )
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
