"""Deterministic mock model provider for CI.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Iterator

from local_agent.model.base import (
    GenerateRequest,
    GenerateResponse,
    ModelCapabilities,
    ModelProvider,
)

logger = logging.getLogger(__name__)
log = logger


class MockProvider(ModelProvider):
    """Deterministic provider — same input always yields same output."""

    def __init__(
        self,
        model_name: str = "mock-model",
        fixtures_dir: str | Path | None = None,
        scenario: str | None = None,
        generate_delay: float = 0.0,
    ) -> None:
        self.model_name = model_name
        self._responses: dict[str, str] = {}
        self._fixture_steps: list[str] = []
        self._fixture_step = 0
        self.generate_delay = generate_delay
        if fixtures_dir is not None and scenario is not None:
            self._load_fixture_scenario(Path(fixtures_dir), scenario)

    def _load_fixture_scenario(self, fixtures_dir: Path, scenario: str) -> None:
        manifest_path = fixtures_dir / scenario / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Fixture manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for step_file in manifest["steps"]:
            step_path = fixtures_dir / scenario / step_file
            self._fixture_steps.append(step_path.read_text(encoding="utf-8").strip())

    def reset(self) -> None:
        self._fixture_step = 0

    def set_response(self, prompt_key: str, response: str) -> None:
        self._responses[prompt_key] = response

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        if self.generate_delay > 0:
            time.sleep(self.generate_delay)
        if self._fixture_steps:
            if self._fixture_step >= len(self._fixture_steps):
                text = json.dumps({"type": "FINAL", "content": "No more fixture steps"})
            else:
                text = self._fixture_steps[self._fixture_step]
                self._fixture_step += 1
            return GenerateResponse(text=text, model=self.model_name)

        if request.prompt in self._responses:
            text = self._responses[request.prompt]
        else:
            digest = hashlib.sha256(request.prompt.encode()).hexdigest()[:16]
            text = json.dumps({
                "type": "FINAL",
                "content": f"mock response for prompt hash {digest}",
            })
        return GenerateResponse(text=text, model=self.model_name)

    def stream(self, request: GenerateRequest) -> Iterator[str]:
        response = self.generate(request)
        chunk_size = max(1, len(response.text) // 4)
        for i in range(0, len(response.text), chunk_size):
            yield response.text[i : i + chunk_size]

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": "mock", "model": self.model_name}

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tools=True,
            max_context_tokens=8192,
            model_name=self.model_name,
        )
