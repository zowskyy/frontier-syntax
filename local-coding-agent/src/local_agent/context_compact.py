"""Compaction helpers for context manager."""

from __future__ import annotations

import re
from typing import Any, Callable


def _estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def enforce_total_budget(messages: list[Any], total_fn: Callable[[], int], ceiling: int) -> None:
    while total_fn() > ceiling and messages:
        droppable = [
            index
            for index, message in enumerate(messages)
            if not message.critical and not message.checkpoint_marker
        ]
        if not droppable:
            break
        del messages[droppable[0]]


def truncate_noncritical_messages(
    messages: list[Any],
    truncate_fn: Callable[[str, int], str],
    message_cls: type,
) -> int:
    updated: list[Any] = []
    truncated = 0
    for message in messages:
        protected = message.critical or message.checkpoint_marker or message.tokens <= 64
        if protected:
            updated.append(message)
            continue
        new_content = truncate_fn(message.content, 64)
        updated.append(
            message_cls(message.role, new_content, _estimate_tokens(new_content), False, False)
        )
        truncated += 1
    messages[:] = updated
    return truncated
