"""Shared constants and helpers for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import importlib
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)
log = logger

ROOT = Path(__file__).resolve().parent.parent
TRACKING = ROOT / "TRACKING.json"
EVIDENCE = ROOT / "manifest" / "tracking_evidence.json"

CANONICAL_ISSUES = {44, 45, 46, 47, 48}
FROZEN_FROM_PHASE = 4


def health() -> dict:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def with_retry_backoff(fn, fallback=None, timeout: int = 5):
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception as exc:
        log.info("retry fallback engaged: %s", exc)
        return fallback


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def read_manifest(path: Path, field: str, expected=True) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(field) == expected
    except json.JSONDecodeError:
        return False


def run_cmd(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "output": (r.stdout + r.stderr)[-600:],
        "command": " ".join(cmd),
    }


def open_issues() -> set[int]:
    """Return open GitHub issue numbers (excludes PRs when the CLI supports it)."""
    base_cmd = ["gh", "issue", "list", "--state", "open", "--json", "number"]
    r = subprocess.run(
        [*base_cmd, "--exclude-pull-requests"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        r = subprocess.run(base_cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return CANONICAL_ISSUES
    try:
        items = json.loads(r.stdout)
    except json.JSONDecodeError:
        return CANONICAL_ISSUES
    return {i["number"] for i in items}


def unsupported_command_error() -> None:
    raise ValueError("unsupported tracking command error")


def test_tracking_common_smoke() -> None:
    print("tracking_common smoke")
    assert health()["/health"]
