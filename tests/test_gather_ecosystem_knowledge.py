#!/usr/bin/env python3
"""Tests for ecosystem knowledge gather (unit, mocked gh)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gather_ecosystem_knowledge as eco  # noqa: E402


class EcosystemGatherTests(unittest.TestCase):
    def test_classify_repo(self) -> None:
        self.assertEqual(eco.classify_repo("frontier-syntax"), "frontier_core")
        self.assertEqual(eco.classify_repo("project-nexus"), "frontier_ecosystem")
        self.assertEqual(eco.classify_repo("jadx"), "fork_or_adjacent")

    def test_infer_claims_extracts_description(self) -> None:
        claims = eco.infer_claims("Cursor IDE in Frontier", "# Title\nself-hosting complete")
        self.assertTrue(any("Cursor IDE" in c for c in claims))

    def test_format_repo_section_has_headers(self) -> None:
        p = eco.RepoProfile(
            name="frontier-syntax",
            url="https://github.com/zowskyy/frontier-syntax",
            description="L",
            is_private=False,
            language="Rust",
            updated_at="2026-08-06",
            category="frontier_core",
            access_status="ok",
            readme_excerpt="# Frontier",
            claims=["test claim"],
            can_do=["can"],
            cannot_do=["cannot"],
            blueprint_relation="canonical",
        )
        text = eco.format_repo_section(p, 1)
        for header in ("WHAT IT IS", "WHAT IT CLAIMS", "VERIFIED", "CANNOT DO", "BLUEPRINT RELATION"):
            self.assertIn(header, text)

    @mock.patch.object(eco, "gh_json")
    @mock.patch.object(eco, "audit_record")
    @mock.patch.object(eco, "load_frontier_syntax_status")
    @mock.patch.object(eco, "write_report")
    def test_dry_run_no_report_write(self, mock_write, mock_status, _audit, mock_gh) -> None:
        mock_gh.return_value = [
            {"name": "frontier-syntax", "description": "", "isPrivate": False, "url": "u", "updatedAt": "t"}
        ]
        mock_status.return_value = {"checks": {}}
        with mock.patch.object(sys, "argv", ["gather_ecosystem_knowledge.py", "--dry-run"]):
            code = eco.main()
        self.assertEqual(code, 0)
        mock_write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
