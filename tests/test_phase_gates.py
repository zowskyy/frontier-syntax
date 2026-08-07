"""Smoke tests for phase 4-7 gate scripts (structure only, no cargo)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PhaseGateScriptTests(unittest.TestCase):
    def test_generate_corpus_produces_min_samples(self) -> None:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/training/generate_corpus.py"), "--count", "1000"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        jsonl = ROOT / "manifest" / "training_corpus" / "frontier_v1.jsonl"
        self.assertTrue(jsonl.exists())
        lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertGreaterEqual(len(lines), 1000)

    def test_agent_security_scan_runs(self) -> None:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_agent_security.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("pass"))


if __name__ == "__main__":
    unittest.main()
