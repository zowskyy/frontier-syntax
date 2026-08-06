#!/usr/bin/env python3
"""Tests for README auto-update via shadow worker markers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import update_audit_readme as updater  # noqa: E402


class ReadmeUpdaterTests(unittest.TestCase):
    def test_patch_file_inserts_markers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "README.md"
            path.write_text("# Title\n\nBody text.\n", encoding="utf-8")
            block = (
                "<!-- SHADOW_WORKER_STATUS:BEGIN -->\n"
                "status here\n"
                "<!-- SHADOW_WORKER_STATUS:END -->\n"
            )
            self.assertTrue(updater.patch_file(path, block))
            text = path.read_text(encoding="utf-8")
            self.assertIn("SHADOW_WORKER_STATUS:BEGIN", text)
            self.assertIn("status here", text)

    def test_patch_file_replaces_existing_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "README.md"
            path.write_text(
                "# T\n\n<!-- SHADOW_WORKER_STATUS:BEGIN -->\nold\n<!-- SHADOW_WORKER_STATUS:END -->\n",
                encoding="utf-8",
            )
            block = (
                "<!-- SHADOW_WORKER_STATUS:BEGIN -->\n"
                "new status\n"
                "<!-- SHADOW_WORKER_STATUS:END -->\n"
            )
            updater.patch_file(path, block)
            text = path.read_text(encoding="utf-8")
            self.assertIn("new status", text)
            self.assertNotIn("old\n<!--", text)

    @mock.patch.object(updater, "collect_status")
    def test_update_readmes_returns_file_map(self, mock_collect) -> None:
        mock_collect.return_value = {
            "updated_at": "2026-08-06",
            "last_activity_utc": "t",
            "session_entry_count": 1,
            "repo_snapshot_id": "snap",
            "ecosystem_run_id": "eco",
            "ecosystem_repos": {"repo_count": 27},
            "benchmark": {"timings_s": {"total_s": 21}, "sla_met": {"total_under_cap": True}},
            "wasm_size_kb": 127.4,
            "wasm_target_met": False,
            "gate": {"phase_0": "PASS", "phase_1": "FAIL", "open_issues": [44]},
        }
        with tempfile.TemporaryDirectory() as td:
            audit_readme = Path(td) / "audit_README.md"
            audit_readme.write_text(
                "<!-- SHADOW_WORKER_STATUS:BEGIN -->\nx\n<!-- SHADOW_WORKER_STATUS:END -->\n",
                encoding="utf-8",
            )
            with mock.patch.object(updater, "TARGETS", [audit_readme]):
                with mock.patch.object(updater, "format_audit_readme_block", return_value="<!-- SHADOW_WORKER_STATUS:BEGIN -->\nok\n<!-- SHADOW_WORKER_STATUS:END -->\n"):
                    with mock.patch.object(updater, "format_root_readme_block", return_value="<!-- SHADOW_WORKER_STATUS:BEGIN -->\nok\n<!-- SHADOW_WORKER_STATUS:END -->\n"):
                        result = updater.update_readmes()
            self.assertIn("files", result)


if __name__ == "__main__":
    unittest.main()
