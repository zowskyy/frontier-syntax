#!/usr/bin/env python3
"""Tests for agent audit logger (hash chain, PII policy)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import agent_audit_logger as logger  # noqa: E402


class AuditLoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = Path(self.tmp.name) / "audit"
        self.sessions = self.audit / "sessions"
        self.state = self.audit / "state"
        self.sessions.mkdir(parents=True)
        self.state.mkdir(parents=True)

        self.patches = [
            mock.patch.object(logger, "AUDIT_ROOT", self.audit),
            mock.patch.object(logger, "SESSIONS", self.sessions),
            mock.patch.object(logger, "STATE_DIR", self.state),
            mock.patch.object(logger, "PRIVATE_PROMPTS", self.state / "private_prompts.jsonl"),
            mock.patch.object(logger, "INDEX", self.audit / "index.json"),
            mock.patch.object(logger, "git_info", return_value={"branch": "test", "commit": "abc"}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_no_user_prompt_in_public_log(self) -> None:
        entry = logger.record(
            session_id="test",
            category="tool_call",
            action="test action",
            why="unit test",
            user_prompt_excerpt="secret user legal request text",
        )
        self.assertNotIn("user_prompt_excerpt", entry)
        self.assertIn("user_prompt_sha256", entry)
        public = (self.sessions / "test.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("secret user legal", public)
        private = (self.state / "private_prompts.jsonl").read_text(encoding="utf-8")
        self.assertIn("secret user legal", private)

    def test_hash_chain(self) -> None:
        e1 = logger.record(session_id="chain", category="pipeline", action="a", why="w")
        e2 = logger.record(session_id="chain", category="pipeline", action="b", why="w")
        self.assertEqual(e2["prev_hash"], e1["entry_hash"])
        self.assertEqual(e2["entry_hash"], logger.compute_entry_hash(e2))


class ValidateAuditTests(unittest.TestCase):
    def test_scrub_removes_pii_field(self) -> None:
        from scrub_audit_sessions import scrub_file

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.jsonl"
            row = {
                "id": "00000000-0000-4000-8000-000000000001",
                "timestamp_utc": "2026-08-06T00:00:00Z",
                "session_id": "s",
                "category": "user_prompt",
                "action": "x",
                "why": "y",
                "how_to_repeat": {
                    "command": "",
                    "script": "",
                    "skill": "",
                    "extension_hook": "",
                    "prerequisites": [],
                },
                "honesty": {"verified_by_execution": False, "omissions": [], "cannot_verify": []},
                "user_prompt_excerpt": "PII text here",
            }
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with mock.patch("scrub_audit_sessions.SESSIONS", Path(td)):
                with mock.patch("scrub_audit_sessions.PRIVATE", Path(td) / "priv.jsonl"):
                    n, moved = scrub_file(path)
            self.assertEqual(moved, 1)
            cleaned = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertNotIn("user_prompt_excerpt", cleaned)
            self.assertIn("entry_hash", cleaned)


if __name__ == "__main__":
    unittest.main()
