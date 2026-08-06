#!/usr/bin/env python3
"""P4: WASM size — delegates to canonical measure_wasm_size.py."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    r = subprocess.run([sys.executable, str(ROOT / "scripts/measure_wasm_size.py")], cwd=ROOT)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
