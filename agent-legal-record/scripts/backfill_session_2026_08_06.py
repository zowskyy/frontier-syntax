#!/usr/bin/env python3
"""Backfill audit entries for frontier-syntax agent sessions (one-time / manual)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGGER = ROOT / "scripts" / "agent_audit_logger.py"
SESSION = "frontier-syntax-2026-08-06"


def log(**kwargs) -> None:
    cmd = [
        sys.executable,
        str(LOGGER),
        "record",
        "--session",
        SESSION,
        "--category",
        kwargs["category"],
        "--action",
        kwargs["action"],
        "--why",
        kwargs["why"],
        "--command",
        kwargs.get("command", ""),
        "--script",
        kwargs.get("script", ""),
        "--skill",
        kwargs.get("skill", ""),
    ]
    if kwargs.get("verified"):
        cmd.append("--verified")
    for o in kwargs.get("omissions", []):
        cmd.extend(["--omission", o])
    for c in kwargs.get("cannot_verify", []):
        cmd.extend(["--cannot-verify", c])
    if kwargs.get("pr_url"):
        cmd.extend(["--pr-url", kwargs["pr_url"]])
    if kwargs.get("user_prompt"):
        cmd.extend(["--user-prompt", kwargs["user_prompt"][:500]])
    subprocess.run(cmd, cwd=ROOT.parent, check=True)


def main() -> int:
    entries = [
        {
            "category": "backfill",
            "action": "Fixed WASM main export index — reorder functions so main is always function 0",
            "why": "wasmtime invoked wrong function in multi-function modules (double+main); user Move forward / Phase 1",
            "command": "git show d426b2b -- src/wasm_codegen.rs",
            "script": "scripts/verify_wasm_codegen.py",
            "skill": "blueprint-phase-1",
            "verified": True,
            "pr_url": "https://github.com/zowskyy/frontier-syntax/pull/57",
            "omissions": ["Independent validator has not closed issue #44"],
        },
        {
            "category": "backfill",
            "action": "Created wasmtime wast verifier (4 cases: const, let/if, while, function_call)",
            "why": "wasmtime run --invoke prints no stdout; wast assert_return is reliable oracle",
            "command": "python3 scripts/verify_wasm_codegen.py",
            "script": "scripts/verify_wasm_codegen.py",
            "verified": True,
            "omissions": ["while test avoids assignment — parser has no assign stmt yet"],
        },
        {
            "category": "backfill",
            "action": "Blueprint v2.0 — WASM primary, native deferred; Phase 6 LoRA corpus plan",
            "why": "User strategic decision: from-scratch LLM not viable; fine-tune after Phase 1",
            "command": "cat PROJECT_BLUEPRINT.md docs/phase6_synthetic_training_plan.md",
            "skill": "agent-audit-record",
            "verified": True,
            "pr_url": "https://github.com/zowskyy/frontier-syntax/pull/58",
        },
        {
            "category": "backfill",
            "action": "Enterprise roadmap + adapted gather_for_review (not verbatim generic command)",
            "why": "User requested practical review gather and enterprise-grade forward plan",
            "command": "bash scripts/gather_for_review.sh",
            "script": "scripts/gather_for_review.sh",
            "verified": True,
            "cannot_verify": [
                "Did not read every line of all 56 Rust files into chat",
                "pie-extension confirmed absent — not searched outside repo",
            ],
            "omissions": [
                "Issues #59-#63 duplicate #44-#48 — re-dedupe not yet executed",
                "B1 silent string/float bug not yet fixed",
            ],
        },
        {
            "category": "limitation",
            "action": "Disclosed: agent cannot run during user idle without scheduler",
            "why": "User requested >5min idle logging; honesty requires stating LLM is not a daemon",
            "skill": "agent-audit-record",
            "verified": True,
            "cannot_verify": ["Cursor desktop chat on user local machine without hooks"],
        },
        {
            "category": "user_prompt",
            "action": "User requested private legal audit repo for all future chat actions",
            "why": "Owner wants legal record with rationale and reproducibility for every action",
            "user_prompt": "make a lot of every action and interaction... private repo... honest... idle >5min",
            "verified": True,
        },
    ]
    for e in entries:
        log(**e)
    print(f"Backfilled {len(entries)} entries to session {SESSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
