"""SLICE 12 — Embedding provider abstraction."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model_id: str
    dimension: int


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> bool:
        raise NotImplementedError

    def embed_batch(self, texts: list[str], *, max_batch_size: int = 32) -> list[EmbeddingResult]:
        results: list[EmbeddingResult] = []
        for index in range(0, len(texts), max_batch_size):
            batch = texts[index : index + max_batch_size]
            results.extend(self.embed(text) for text in batch)
        return results


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embeddings for tests and offline development."""

    def __init__(self, model_id: str = "mock-embed-v1", dimension: int = 8, healthy: bool = True) -> None:
        self._model_id = model_id
        self._dimension = dimension
        self._healthy = healthy

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def health(self) -> bool:
        return self._healthy

    def embed(self, text: str) -> EmbeddingResult:
        if not self._healthy:
            raise RuntimeError("Embedding provider is unhealthy")
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(self._dimension):
            byte = digest[index % len(digest)]
            values.append((byte / 255.0) * 2.0 - 1.0)
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        normalized = [value / norm for value in values]
        return EmbeddingResult(normalized, self._model_id, self._dimension)
