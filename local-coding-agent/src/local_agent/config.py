"""Validated agent configuration.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
log = logger


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    MOCK = "mock"


class AgentConfig(BaseSettings):
    """Schema-validated agent configuration.

    Secrets are resolved from environment only (never stored in config files).
    """

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    workspace_root: Path = Field(default=Path.cwd())
    database_path: Path = Field(default=Path(".local_agent/agent.db"))
    model_provider: ModelProvider = Field(default=ModelProvider.MOCK)
    model_name: str = Field(default="mock-model")
    embedding_provider: str = Field(default="mock")
    embedding_model: str = Field(default="mock-embed")
    max_file_size: int = Field(default=1_048_576, ge=1)
    max_output_size: int = Field(default=65_536, ge=1)
    tool_timeout: int = Field(default=120, ge=1)
    network_enabled: bool = Field(default=False)
    plugin_enabled: bool = Field(default=False)

    @field_validator("workspace_root", "database_path", mode="before")
    @classmethod
    def _expand_path(cls, value: object) -> Path:
        if value is None:
            raise ValueError("path must not be None")
        path = Path(str(value)).expanduser().resolve()
        return path

    @field_validator("workspace_root")
    @classmethod
    def _workspace_must_exist(cls, value: Path) -> Path:
        if not value.is_dir():
            raise ValueError(f"workspace_root does not exist or is not a directory: {value}")
        return value

    def resolve_secret(self, env_key: str) -> Optional[str]:
        """Resolve a secret from environment only."""
        import os

        return os.environ.get(env_key)


def load_config(**overrides: object) -> AgentConfig:
    """Load and validate configuration, raising actionable errors on failure."""
    try:
        config = AgentConfig(**overrides)  # type: ignore[arg-type]
        log.info(
            "loaded config workspace=%s model_provider=%s network=%s",
            config.workspace_root,
            config.model_provider.value,
            config.network_enabled,
        )
        return config
    except Exception as exc:
        raise ValueError(f"invalid configuration: {exc}") from exc
