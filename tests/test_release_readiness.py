"""Tests for scripts/release_readiness.py"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "release_readiness.py"


class ReleaseReadinessTests(unittest.TestCase):
    def test_audit_skip_run(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--audit", "--skip-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn(data["verdict"], ("RC_READY", "RELEASE_READY", "NOT_READY"))
        self.assertTrue((ROOT / "manifest" / "release_readiness.json").exists())
        self.assertTrue((ROOT / "audit_reports" / "RELEASE_READINESS_REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()
