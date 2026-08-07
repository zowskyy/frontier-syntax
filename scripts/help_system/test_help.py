#!/usr/bin/env python3
"""Tests for the Get Help system."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from help_system.classify import RequestKind, classify_request  # noqa: E402
from help_system.config import find_repo_root, load_config  # noqa: E402
from help_system.store import HelpRequest, HelpRequestStore  # noqa: E402
from help_system.respond import format_blocked_summary  # noqa: E402
from help_system.stalled import StalledReport  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_bug_detection(self):
        c = classify_request("my build fails with an error")
        self.assertEqual(c.kind, RequestKind.BUG)

    def test_blocked_detection(self):
        c = classify_request("nothing is moving forward, everything is stalled")
        self.assertEqual(c.kind, RequestKind.BLOCKED)

    def test_status_detection(self):
        c = classify_request("what's the status of my request")
        self.assertEqual(c.kind, RequestKind.STATUS)


class TestStore(unittest.TestCase):
    def test_add_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requests.jsonl"
            store = HelpRequestStore(path)
            req = HelpRequest.new("test-repo", "help me", "bug")
            store.add(req)
            found = store.get(req.id)
            self.assertIsNotNone(found)
            self.assertEqual(found.user_text, "help me")

    def test_list_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requests.jsonl"
            store = HelpRequestStore(path)
            req = HelpRequest.new("repo-a", "stuck", "stuck")
            store.add(req)
            open_items = store.list_open("repo-a")
            self.assertEqual(len(open_items), 1)


class TestConfig(unittest.TestCase):
    def test_find_repo_root(self):
        root = find_repo_root(ROOT)
        self.assertTrue((root / ".git").exists())

    def test_load_config(self):
        config = load_config(ROOT)
        self.assertEqual(config.repo_id, "frontier-syntax")


class TestRespond(unittest.TestCase):
    def test_empty_blocked(self):
        text = format_blocked_summary([StalledReport(repo_id="test", items=[])])
        self.assertIn("clear", text.lower())


if __name__ == "__main__":
    unittest.main()
