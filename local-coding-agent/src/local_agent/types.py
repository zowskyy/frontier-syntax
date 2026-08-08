"""Shared types for the local coding agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    PLAN = "plan"
    RETRIEVE = "retrieve"
    MODEL = "model"
    VALIDATE = "validate"
    POLICY = "policy"
    TOOL = "tool"
    OBSERVE = "observe"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"


class ModelResponseType(str, Enum):
    FINAL = "FINAL"
    TOOL_CALL = "TOOL_CALL"
    EDIT_REQUEST = "EDIT_REQUEST"
    CLARIFICATION = "CLARIFICATION"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class ToolRiskClass(str, Enum):
    READ_ONLY = "read_only"
    MUTATING_APPROVAL = "mutating_approval"
    HIGH_RISK = "high_risk"


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    required_approval: bool = False
    capability_scope: list[str] = field(default_factory=list)


@dataclass
class ModelResponse:
    response_type: ModelResponseType
    content: dict[str, Any]
    raw: str = ""

    @property
    def tool_name(self) -> str | None:
        if self.response_type != ModelResponseType.TOOL_CALL:
            return None
        return self.content.get("tool")

    @property
    def tool_args(self) -> dict[str, Any]:
        if self.response_type != ModelResponseType.TOOL_CALL:
            return {}
        return self.content.get("arguments", {})


@dataclass
class ToolResult:
    tool: str
    success: bool
    output: Any
    error: str | None = None


@dataclass
class AgentTask:
    task_id: str
    prompt: str
    state: AgentState = AgentState.PLAN
    conversation: list[dict[str, Any]] = field(default_factory=list)
    observations: list[ToolResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
