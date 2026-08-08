"""Tool registry with risk metadata.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)
log = logger


class ToolRiskClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATING_APPROVAL = "MUTATING_APPROVAL"
    HIGH_RISK = "HIGH_RISK"


@dataclass
class ToolSpec:
    name: str
    description: str
    risk_class: ToolRiskClass
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., dict[str, Any]]] = None


class ToolRegistry:
    """Registry of available tools with risk metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec
        log.info("registered tool %s risk=%s", spec.name, spec.risk_class.value)

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def list_by_risk(self, risk_class: ToolRiskClass) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.risk_class == risk_class]

    def execute(self, name: str, arguments: dict[str, Any], context: Any = None) -> dict[str, Any]:
        spec = self._tools.get(name)
        if spec is None:
            return {"success": False, "error": f"unknown tool: {name}"}
        if spec.handler is None:
            return {"success": False, "error": f"no handler for tool: {name}"}
        try:
            result = spec.handler(arguments, context)
            return {"success": True, **result}
        except Exception as exc:
            log.exception("tool %s failed", name)
            return {"success": False, "error": str(exc)}

    def to_policy_table(self) -> list[dict[str, Any]]:
        """Expose tool list to policy engine."""
        return [
            {
                "name": t.name,
                "risk_class": t.risk_class.value,
                "description": t.description,
            }
            for t in self._tools.values()
        ]
