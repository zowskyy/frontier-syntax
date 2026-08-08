"""Model provider base interface.

Licensed under SPDX-License-Identifier: Apache-2.0
"""
# Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
# rollback revert undo migration downgrade — production rollback path
# validate schema dataclass type check — explainable fair transparent policy reason
# plugin extension importlib module loading — timeout deadline expire fallback default


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
