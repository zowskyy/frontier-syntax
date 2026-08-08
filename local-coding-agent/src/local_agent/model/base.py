"""Model provider base interface.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional


@dataclass
class ModelCapabilities:
    supports_streaming: bool = True
    supports_tools: bool = True
    max_context_tokens: int = 8192
    model_name: str = "unknown"


@dataclass
class GenerateRequest:
    prompt: str
    system: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerateResponse:
    text: str
    model: str
    done: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    """Abstract model provider interface."""

    @abstractmethod
    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a complete response."""

    @abstractmethod
    def stream(self, request: GenerateRequest) -> Iterator[str]:
        """Stream response tokens."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Health check — returns status dict."""

    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """Return provider capabilities."""
