"""Tests for model providers (SLICE 4).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json

import pytest

from local_agent.model.base import GenerateRequest
from local_agent.model.mock import MockProvider
from local_agent.model.ollama import OllamaProvider
from local_agent.model.llama_cpp import LlamaCppProvider


def test_mock_provider_deterministic() -> None:
    provider = MockProvider("test-mock")
    req = GenerateRequest(prompt="hello world")
    r1 = provider.generate(req)
    r2 = provider.generate(req)
    assert r1.text == r2.text
    assert r1.model == "test-mock"


def test_mock_provider_custom_response() -> None:
    provider = MockProvider()
    provider.set_response("custom", json.dumps({"type": "FINAL", "content": "done"}))
    resp = provider.generate(GenerateRequest(prompt="custom"))
    assert "done" in resp.text


def test_mock_provider_stream() -> None:
    provider = MockProvider()
    req = GenerateRequest(prompt="stream test")
    chunks = list(provider.stream(req))
    full = "".join(chunks)
    resp = provider.generate(req)
    assert full == resp.text


def test_mock_provider_health() -> None:
    provider = MockProvider("m1")
    health = provider.health()
    assert health["status"] == "ok"
    assert health["provider"] == "mock"


def test_mock_provider_capabilities() -> None:
    provider = MockProvider("m1")
    caps = provider.capabilities()
    assert caps.supports_streaming is True
    assert caps.model_name == "m1"


def test_ollama_provider_health_unavailable() -> None:
    provider = OllamaProvider(model_name="nonexistent", base_url="http://127.0.0.1:19999")
    health = provider.health()
    assert health["status"] == "unavailable"


def test_ollama_provider_capabilities() -> None:
    provider = OllamaProvider()
    caps = provider.capabilities()
    assert caps.supports_streaming is True
    assert caps.max_context_tokens > 0


def test_llama_cpp_health_missing_file() -> None:
    provider = LlamaCppProvider(model_path="/nonexistent/model.gguf")
    health = provider.health()
    assert health["status"] == "unavailable"


def test_llama_cpp_capabilities() -> None:
    provider = LlamaCppProvider(model_path="/tmp/model.gguf", n_ctx=2048)
    caps = provider.capabilities()
    assert caps.max_context_tokens == 2048
