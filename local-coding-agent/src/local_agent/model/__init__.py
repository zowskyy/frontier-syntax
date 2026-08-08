"""Model provider package.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from local_agent.model.base import (
    GenerateRequest,
    GenerateResponse,
    ModelCapabilities,
    ModelProvider,
)
from local_agent.model.llama_cpp import LlamaCppProvider
from local_agent.model.mock import MockProvider
from local_agent.model.ollama import OllamaProvider

__all__ = [
    "GenerateRequest",
    "GenerateResponse",
    "LlamaCppProvider",
    "MockProvider",
    "ModelCapabilities",
    "ModelProvider",
    "OllamaProvider",
]
