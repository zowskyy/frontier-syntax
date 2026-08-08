"""Ollama HTTP model provider.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Iterator

from local_agent.model.base import (
    GenerateRequest,
    GenerateResponse,
    ModelCapabilities,
    ModelProvider,
)

logger = logging.getLogger(__name__)
log = logger


class OllamaProvider(ModelProvider):
    """Local HTTP inference via Ollama API."""

    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 120,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.system:
            payload["system"] = request.system
        result = self._post("/api/generate", payload)
        return GenerateResponse(
            text=result.get("response", ""),
            model=self.model_name,
            metadata={"eval_count": result.get("eval_count")},
        )

    def stream(self, request: GenerateRequest) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": request.prompt,
            "stream": True,
        }
        url = f"{self.base_url}/api/generate"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for line in resp:
                chunk = json.loads(line.decode())
                if "response" in chunk:
                    yield chunk["response"]

    def health(self) -> dict[str, Any]:
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            available = any(self.model_name in m for m in models)
            return {
                "status": "ok" if available else "model_not_found",
                "provider": "ollama",
                "model": self.model_name,
                "models": models,
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": "unavailable", "provider": "ollama", "error": str(exc)}

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tools=True,
            max_context_tokens=32768,
            model_name=self.model_name,
        )
