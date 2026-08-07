"""Phase 8 launch gate smoke test."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Phase8LaunchTests(unittest.TestCase):
    def test_verify_phase8_passes(self) -> None:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_phase8_launch.py"), "--skip-url-check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("pass"))


if __name__ == "__main__":
    unittest.main()
