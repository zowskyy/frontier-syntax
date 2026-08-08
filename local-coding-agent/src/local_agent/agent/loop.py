"""Core agent loop orchestration (SLICE 17)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from local_agent.context import ContextManager
from local_agent.model.base import GenerateRequest, ModelProvider
from local_agent.model.mock import MockProvider
from local_agent.output import ResponseType, parse_model_output
from local_agent.policy import PolicyEngine
from local_agent.tools.handlers import ToolContext, create_default_registry
from local_agent.tools.registry import ToolRegistry
from local_agent.types import AgentState, AgentTask, ToolResult


class AgentLoopError(Exception):
    """Base error for agent loop failures."""


class AgentTimeoutError(AgentLoopError):
    """Raised when agent loop exceeds timeout."""


class AgentCancelledError(AgentLoopError):
    """Raised when agent loop is cancelled."""


@dataclass
class AgentLoopResult:
    task_id: str
    final_state: AgentState
    message: str
    observations: list[ToolResult] = field(default_factory=list)
    steps_executed: int = 0
    elapsed_ms: float = 0.0


@dataclass
class SimpleRetrieval:
    """Lightweight retrieval stub for agent-loop tests without full knowledge store."""

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        return [
            {
                "source": "fixture",
                "content": f"Retrieved context for: {query}",
                "trust_level": "T2",
                "untrusted": True,
            }
        ]


class AgentLoop:
    """Core agent loop: plan → retrieve → model → validate → policy → tool → observe."""

    def __init__(
        self,
        provider: ModelProvider,
        workspace_root: str | Path | None = None,
        policy: PolicyEngine | None = None,
        tools: ToolRegistry | None = None,
        retrieval: SimpleRetrieval | None = None,
        context: ContextManager | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.provider = provider
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.policy = policy or PolicyEngine()
        self.tools = tools or create_default_registry()
        self.tool_context = ToolContext(workspace_root=self.workspace_root)
        self.retrieval = retrieval or SimpleRetrieval()
        self.context = context or ContextManager()
        self.timeout_seconds = timeout_seconds
        self._cancelled = False
        self._current_response: str = ""

    def cancel(self) -> None:
        self._cancelled = True

    def run(self, prompt: str, task_id: str | None = None) -> AgentLoopResult:
        task = AgentTask(task_id=task_id or str(uuid.uuid4()), prompt=prompt)
        start = time.monotonic()
        steps = 0
        deadline = start + self.timeout_seconds

        if isinstance(self.provider, MockProvider):
            self.provider.reset()

        try:
            while task.state not in (AgentState.COMPLETE, AgentState.FAILED, AgentState.CANCELLED):
                if self._cancelled:
                    task.state = AgentState.CANCELLED
                    break
                if time.monotonic() > deadline:
                    raise AgentTimeoutError(f"Agent loop timed out after {self.timeout_seconds}s")

                task.state = self._step(task)
                steps += 1

            elapsed = (time.monotonic() - start) * 1000
            return AgentLoopResult(
                task_id=task.task_id,
                final_state=task.state,
                message=self._final_message(task),
                observations=task.observations,
                steps_executed=steps,
                elapsed_ms=elapsed,
            )
        except AgentTimeoutError:
            task.state = AgentState.RECOVERY_REQUIRED
            raise

    def _step(self, task: AgentTask) -> AgentState:
        if task.state == AgentState.PLAN:
            task.conversation.append({"role": "system", "content": "Planning task execution"})
            task.metadata["plan"] = {"goal": task.prompt, "steps": ["retrieve", "act", "observe"]}
            return AgentState.RETRIEVE

        if task.state == AgentState.RETRIEVE:
            chunks = self.retrieval.retrieve(task.prompt)
            self.context.add_retrieved(chunks)
            task.metadata["retrieved_chunks"] = len(chunks)
            return AgentState.MODEL

        if task.state == AgentState.MODEL:
            messages = self.context.build_messages(task.prompt)
            prompt = messages[-1]["content"] if messages else task.prompt
            response = self.provider.generate(GenerateRequest(prompt=prompt))
            raw = response.text
            task.conversation.append({"role": "assistant", "content": raw})
            self._current_response = raw
            return AgentState.VALIDATE

        if task.state == AgentState.VALIDATE:
            parsed = parse_model_output(self._current_response)
            task.metadata["parsed_response"] = parsed
            if not parsed.valid:
                return AgentState.FAILED
            if parsed.response_type == ResponseType.FINAL:
                return AgentState.COMPLETE
            if parsed.response_type == ResponseType.TOOL_CALL:
                return AgentState.POLICY
            if parsed.response_type == ResponseType.CLARIFICATION:
                return AgentState.COMPLETE
            return AgentState.FAILED

        if task.state == AgentState.POLICY:
            parsed = task.metadata["parsed_response"]
            tool_name = parsed.data.get("tool", "")
            tool_args = parsed.data.get("arguments", {})
            decision = self.policy.authorize(tool_name, tool_args)
            task.metadata["policy_decision"] = decision
            if not decision.allowed:
                return AgentState.FAILED
            return AgentState.TOOL

        if task.state == AgentState.TOOL:
            parsed = task.metadata["parsed_response"]
            tool_name = parsed.data.get("tool", "")
            tool_args = parsed.data.get("arguments", {})
            raw_result = self.tools.execute(tool_name, tool_args, self.tool_context)
            result = ToolResult(
                tool=tool_name,
                success=raw_result.get("success", False),
                output=raw_result,
                error=raw_result.get("error"),
            )
            task.observations.append(result)
            task.metadata["last_tool_result"] = result
            if not result.success:
                return AgentState.FAILED
            return AgentState.OBSERVE

        if task.state == AgentState.OBSERVE:
            result = task.metadata.get("last_tool_result")
            if result:
                self.context.add_message("tool", str(result.output))
            return AgentState.MODEL

        return task.state

    def _final_message(self, task: AgentTask) -> str:
        if task.state == AgentState.COMPLETE:
            parsed = task.metadata.get("parsed_response")
            if parsed and parsed.response_type == ResponseType.FINAL:
                return str(parsed.data.get("content", "Task completed"))
            return "Task completed"
        if task.state == AgentState.CANCELLED:
            return "Task cancelled"
        if task.state == AgentState.FAILED:
            decision = task.metadata.get("policy_decision")
            if decision and not decision.allowed:
                return f"Policy denied: {decision.reason}"
            result = task.metadata.get("last_tool_result")
            if result and not result.success:
                return f"Tool failed: {result.error}"
            parsed = task.metadata.get("parsed_response")
            if parsed and not parsed.valid:
                return f"Validation failed: {parsed.error}"
            return "Task failed"
        return str(task.state.value)

    def to_checkpoint_state(self, task: AgentTask) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "prompt": task.prompt,
            "state": task.state.value,
            "conversation": task.conversation,
            "observations": [
                {"tool": o.tool, "success": o.success, "output": o.output, "error": o.error}
                for o in task.observations
            ],
            "metadata": _serialize_metadata(task.metadata),
        }


def _serialize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    from dataclasses import asdict

    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if hasattr(value, "__dataclass_fields__"):
            result[key] = asdict(value)
        elif hasattr(value, "response_type"):
            result[key] = {
                "type": value.response_type.value,
                "data": value.data,
                "valid": value.valid,
            }
        else:
            result[key] = value
    return result
