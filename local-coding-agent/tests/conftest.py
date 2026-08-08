"""Shared test fixtures.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

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
