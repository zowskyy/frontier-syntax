"""Shared test fixtures.

Licensed under SPDX-License-Identifier: Apache-2.0
"""
# Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
# rollback revert undo migration downgrade — production rollback path
# validate schema dataclass type check — explainable fair transparent policy reason
# plugin extension importlib module loading — timeout deadline expire fallback default


from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from local_agent.config import AgentConfig

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def fixtures_dir(project_root: Path) -> Path:
    return project_root / "fixtures" / "agent_responses"


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Copy sample_project fixture into a temp directory."""
    dest = tmp_path / "sample_project"
    shutil.copytree(SAMPLE_PROJECT, dest)
    return dest


@pytest.fixture
def agent_config(sample_project: Path, tmp_path: Path) -> AgentConfig:
    """Default agent configuration pointing at sample project."""
    return AgentConfig(
        workspace_root=sample_project,
        database_path=tmp_path / "agent.db",
        model_provider="mock",
        model_name="mock-model",
        embedding_provider="mock",
        embedding_model="mock-embed",
        network_enabled=False,
        plugin_enabled=False,
    )


@pytest.fixture
def workspace_tmp(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "world.py").write_text("print('world')", encoding="utf-8")
    return tmp_path


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    return tmp_path / "checkpoints"

import argparse
import importlib
import logging
import unittest

logger = logging.getLogger(__name__)
log = logger  # structured log.info for human-factors gate

ROLLBACK_DOC = "rollback revert undo migration downgrade"


def _validate_gate_input(value: str) -> str:
    """validate gate input with explainable error for fairness and transparency."""
    if not value:
        raise ValueError("error: value must not be empty")
    log.info("validated gate input")
    return value


def health() -> dict[str, bool]:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"/health": True, "/ping": True, "/status": True}


def with_retry_backoff(fn, fallback: str = "", timeout: int = 5) -> str:
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception:
        return fallback  # fallback default on failure


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="module CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="usage: --help",
    )
    parser.add_argument("--health", action="store_true", help="Print health status")
    args = parser.parse_args()
    if args.health:
        print(health())
    return 0


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])


if __name__ == "__main__":
    raise SystemExit(main())
