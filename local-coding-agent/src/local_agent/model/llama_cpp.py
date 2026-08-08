"""llama.cpp direct GGUF inference provider.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

from local_agent.model.base import (
    GenerateRequest,
    GenerateResponse,
    ModelCapabilities,
    ModelProvider,
)

logger = logging.getLogger(__name__)
log = logger


class LlamaCppProvider(ModelProvider):
    """Direct GGUF inference via llama-cpp-python (optional dependency)."""

    def __init__(
        self,
        model_path: str,
        model_name: str = "llama-cpp",
        n_ctx: int = 4096,
    ) -> None:
        self.model_path = model_path
        self.model_name = model_name
        self.n_ctx = n_ctx
        self._llm: Any = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            try:
                from llama_cpp import Llama  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "llama-cpp-python not installed; pip install llama-cpp-python"
                ) from exc
            self._llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx, verbose=False)
        return self._llm

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        llm = self._get_llm()
        result = llm(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        text = result["choices"][0]["text"]
        return GenerateResponse(text=text, model=self.model_name)

    def stream(self, request: GenerateRequest) -> Iterator[str]:
        llm = self._get_llm()
        for chunk in llm(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True,
        ):
            token = chunk["choices"][0].get("text", "")
            if token:
                yield token

    def health(self) -> dict[str, Any]:
        from pathlib import Path

        path = Path(self.model_path)
        if not path.is_file():
            return {
                "status": "unavailable",
                "provider": "llama_cpp",
                "error": f"model file not found: {self.model_path}",
            }
        try:
            self._get_llm()
            return {"status": "ok", "provider": "llama_cpp", "model": self.model_name}
        except Exception as exc:
            return {"status": "unavailable", "provider": "llama_cpp", "error": str(exc)}

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tools=False,
            max_context_tokens=self.n_ctx,
            model_name=self.model_name,
        )
