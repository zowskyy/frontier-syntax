#!/usr/bin/env python3
"""Verify Frontier self-hosting bootstrap (Genesis compile)."""

from __future__ import annotations

import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "frontier" / "src" / "main.fr"


def run(cmd: list[str], cwd: Path = ROOT) -> tuple[bool, str]:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0, out


def main() -> int:
    if not MAIN.exists():
        print(f"FAIL: {MAIN} not found")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bootstrap = tmp_path / "bootstrap"
        self_hosted = tmp_path / "self_hosted"
        launcher = tmp_path / "bootstrap.run"

        ok, out = run(
            [
                "cargo",
                "run",
                "--quiet",
                "--bin",
                "frontier",
                "--",
                "compile",
                str(MAIN),
                "--bootstrap",
                "-o",
                str(bootstrap),
            ]
        )
        if not ok:
            print(f"FAIL: genesis compile\n{out}")
            return 1

        if not bootstrap.exists():
            print("FAIL: bootstrap artifact not created")
            return 1

        if not launcher.exists():
            print("FAIL: bootstrap.run launcher not created")
            return 1

        ok, out = run([str(launcher), "compile", str(MAIN), "-o", str(self_hosted)])
        if not ok:
            print(f"FAIL: bootstrap recompile\n{out}")
            return 1

        if not self_hosted.exists():
            print("FAIL: self_hosted artifact not created")
            return 1

        if not filecmp.cmp(bootstrap, self_hosted, shallow=False):
            print("FAIL: bootstrap and self_hosted differ")
            return 1

    print("PASS: Self-hosting bootstrap (cmp identical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
