"""Tests for configuration (SLICE 1).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.config import AgentConfig, ModelProvider, load_config


def test_default_config(sample_project: Path, tmp_path: Path) -> None:
    config = AgentConfig(
        workspace_root=sample_project,
        database_path=tmp_path / "db.sqlite",
    )
    assert config.model_provider == ModelProvider.MOCK
    assert config.network_enabled is False
    assert config.plugin_enabled is False
    assert config.max_file_size == 1_048_576


def test_model_provider_values() -> None:
    assert ModelProvider.OLLAMA.value == "ollama"
    assert ModelProvider.LLAMA_CPP.value == "llama_cpp"
    assert ModelProvider.MOCK.value == "mock"


def test_invalid_workspace_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workspace_root"):
        load_config(workspace_root=tmp_path / "nonexistent")


def test_load_config_overrides(sample_project: Path, tmp_path: Path) -> None:
    config = load_config(
        workspace_root=sample_project,
        database_path=tmp_path / "agent.db",
        model_provider="mock",
        model_name="test-model",
        network_enabled=False,
    )
    assert config.model_name == "test-model"
    assert config.embedding_provider == "mock"


def test_resolve_secret_from_env(monkeypatch: pytest.MonkeyPatch, sample_project: Path) -> None:
    monkeypatch.setenv("API_KEY", "secret-value")
    config = AgentConfig(workspace_root=sample_project)
    assert config.resolve_secret("API_KEY") == "secret-value"
    assert config.resolve_secret("NONEXISTENT") is None


def test_path_expansion(sample_project: Path) -> None:
    config = AgentConfig(workspace_root=sample_project)
    assert config.workspace_root.is_absolute()
