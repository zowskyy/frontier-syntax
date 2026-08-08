"""SLICE 16 — Agent context manager with token budgeting and compaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class ContextPhase(str, Enum):
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    ACTING = "acting"
    OBSERVING = "observing"


DEFAULT_PHASE_BUDGETS: dict[ContextPhase, int] = {
    ContextPhase.PLANNING: 2048,
    ContextPhase.RETRIEVING: 4096,
    ContextPhase.ACTING: 8192,
    ContextPhase.OBSERVING: 4096,
}


@dataclass
class ContextMessage:
    role: str
    content: str
    tokens: int
    critical: bool = False
    checkpoint_marker: bool = False


@dataclass
class ContextBudget:
    total_tokens: int
    phase_budgets: dict[ContextPhase, int] = field(default_factory=lambda: dict(DEFAULT_PHASE_BUDGETS))
    retrieved_limit: int = 2048


@dataclass(frozen=True)
class CompactionResult:
    messages: list[ContextMessage]
    removed_count: int
    truncated_count: int
    total_tokens: int
    checkpoint_boundary: bool


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


class ContextManager:
    """Manage conversation and retrieved context within token ceilings."""

    def __init__(self, budget: ContextBudget | None = None, token_budget: int = 8000) -> None:
        self.budget = budget or ContextBudget(total_tokens=token_budget)
        self.messages: list[ContextMessage] = []
        self.retrieved_context: str = ""

    def add_message(self, role: str, content: str, *, critical: bool = False) -> ContextMessage:
        message = ContextMessage(role=role, content=content, tokens=estimate_tokens(content), critical=critical)
        self.messages.append(message)
        self._enforce_total_budget()
        return message

    def set_retrieved_context(self, content: str) -> str:
        if estimate_tokens(content) <= self.budget.retrieved_limit:
            self.retrieved_context = content
            return self.retrieved_context
        self.retrieved_context = self.truncate_to_tokens(content, self.budget.retrieved_limit)
        return self.retrieved_context

    def add_retrieved(self, chunks: list[dict[str, Any]]) -> None:
        """Backward-compatible hook used by the agent loop."""
        wrapped = "\n".join(f"[UNTRUSTED] {chunk.get('content', '')}" for chunk in chunks)
        self.set_retrieved_context(f"Retrieved knowledge:\n{wrapped}")

    def build_messages(self, task_prompt: str) -> list[dict[str, Any]]:
        """Backward-compatible message assembly used by the agent loop."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": task_prompt}]
        for message in self.messages:
            messages.append({"role": message.role, "content": message.content})
        return messages

    def estimate_tokens(self) -> int:
        return self.total_tokens()

    def should_checkpoint(self) -> bool:
        return self.total_tokens() > int(self.budget.total_tokens * 0.8)

    def phase_budget(self, phase: ContextPhase) -> int:
        return self.budget.phase_budgets.get(phase, self.budget.total_tokens)

    def assemble_for_phase(self, phase: ContextPhase) -> str:
        ceiling = min(self.phase_budget(phase), self.budget.total_tokens)
        parts: list[str] = []
        if self.retrieved_context:
            parts.append(self.retrieved_context)
        for message in self.messages:
            parts.append(f"{message.role.upper()}: {message.content}")
        combined = "\n\n".join(parts)
        return self.truncate_to_tokens(combined, ceiling)

    def compact(self, *, preserve_critical: bool = True, checkpoint_before: bool = False) -> CompactionResult:
        if checkpoint_before:
            self.mark_checkpoint_boundary()

        removed = 0
        truncated = 0
        kept: list[ContextMessage] = []
        for message in self.messages:
            if preserve_critical and message.critical:
                kept.append(message)
                continue
            if message.checkpoint_marker:
                kept.append(message)
                continue
            removed += 1

        if not kept and self.messages:
            kept = [self.messages[-1]]
            removed = len(self.messages) - 1

        self.messages = kept
        self._enforce_total_budget()
        truncated = self._truncate_noncritical_messages()

        total = self.total_tokens()
        return CompactionResult(
            messages=list(self.messages),
            removed_count=removed,
            truncated_count=truncated,
            total_tokens=total,
            checkpoint_boundary=checkpoint_before,
        )

    def mark_checkpoint_boundary(self) -> ContextMessage:
        marker = ContextMessage(
            role="system",
            content="--- CHECKPOINT_BOUNDARY ---",
            tokens=estimate_tokens("--- CHECKPOINT_BOUNDARY ---"),
            critical=True,
            checkpoint_marker=True,
        )
        self.messages.append(marker)
        return marker

    def total_tokens(self) -> int:
        message_tokens = sum(message.tokens for message in self.messages)
        retrieved_tokens = estimate_tokens(self.retrieved_context) if self.retrieved_context else 0
        return message_tokens + retrieved_tokens

    def _enforce_total_budget(self) -> None:
        while self.total_tokens() > self.budget.total_tokens and self.messages:
            removed = False
            for index, message in enumerate(self.messages):
                if message.critical or message.checkpoint_marker:
                    continue
                del self.messages[index]
                removed = True
                break
            if not removed:
                oldest = self.messages[0]
                if not oldest.critical:
                    self.messages[0] = ContextMessage(
                        role=oldest.role,
                        content=self.truncate_to_tokens(oldest.content, max(1, oldest.tokens // 2)),
                        tokens=max(1, oldest.tokens // 2),
                        critical=oldest.critical,
                        checkpoint_marker=oldest.checkpoint_marker,
                    )
                else:
                    break

    def _truncate_noncritical_messages(self) -> int:
        truncated = 0
        for index, message in enumerate(self.messages):
            if message.critical or message.checkpoint_marker:
                continue
            if message.tokens > 64:
                new_content = self.truncate_to_tokens(message.content, 64)
                self.messages[index] = ContextMessage(
                    role=message.role,
                    content=new_content,
                    tokens=estimate_tokens(new_content),
                    critical=False,
                    checkpoint_marker=False,
                )
                truncated += 1
        return truncated

    @staticmethod
    def truncate_to_tokens(text: str, max_tokens: int) -> str:
        tokens = re.findall(r"\S+", text)
        if len(tokens) <= max_tokens:
            return text
        suffix = "\n...[truncated]"
        suffix_tokens = estimate_tokens(suffix)
        keep = max(1, max_tokens - suffix_tokens)
        truncated = " ".join(tokens[:keep])
        return truncated + suffix
