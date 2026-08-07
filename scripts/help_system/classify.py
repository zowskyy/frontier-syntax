"""Classify user help requests into actionable categories."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RequestKind(str, Enum):
    QUESTION = "question"
    BUG = "bug"
    STUCK = "stuck"
    FEATURE = "feature"
    STATUS = "status"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class Classification:
    kind: RequestKind
    confidence: float
    summary: str
    suggested_action: str


STATUS_PATTERNS = [
    r"\b(status|update|progress|what'?s happening|where are we)\b",
    r"\b(request|ticket)\s*#?H?-?\d+\b",
]
BLOCKED_PATTERNS = [
    r"\b(blocked|stalled|stuck|waiting|nothing (is )?moving|stalling)\b",
    r"\b(what'?s blocking|why (is|are) .* slow)\b",
]
BUG_PATTERNS = [
    r"\b(broken|fails?|error|crash|bug|doesn'?t work|not working)\b",
    r"\b(fix|broken build|compile fail)\b",
]
FEATURE_PATTERNS = [
    r"\b(add|feature|want|need|could you|please implement)\b",
    r"\b(improve|enhancement|support for)\b",
]
QUESTION_PATTERNS = [
    r"\b(how (do|to)|what is|explain|help me understand|where is)\b",
    r"\?$",
]
STUCK_PATTERNS = [
    r"\b(can'?t (merge|push|deploy|proceed)|merge conflict|pr (stuck|blocked))\b",
]


def classify_request(text: str) -> Classification:
    normalized = text.strip().lower()
    if not normalized:
        return Classification(
            kind=RequestKind.UNKNOWN,
            confidence=0.0,
            summary="Empty request",
            suggested_action="Describe what you need help with.",
        )

    if any(re.search(p, normalized) for p in STATUS_PATTERNS):
        return Classification(
            kind=RequestKind.STATUS,
            confidence=0.9,
            summary="Status check",
            suggested_action="Show request and work-item status.",
        )

    if any(re.search(p, normalized) for p in BLOCKED_PATTERNS):
        return Classification(
            kind=RequestKind.BLOCKED,
            confidence=0.85,
            summary="Blocked work scan",
            suggested_action="Scan for stalled issues, PRs, and gate failures.",
        )

    scores: dict[RequestKind, float] = {
        RequestKind.BUG: _score(normalized, BUG_PATTERNS),
        RequestKind.FEATURE: _score(normalized, FEATURE_PATTERNS),
        RequestKind.QUESTION: _score(normalized, QUESTION_PATTERNS),
        RequestKind.STUCK: _score(normalized, STUCK_PATTERNS),
    }

    best_kind = max(scores, key=scores.get)
    best_score = scores[best_kind]

    if best_score < 0.3:
        return Classification(
            kind=RequestKind.UNKNOWN,
            confidence=0.3,
            summary=text[:120],
            suggested_action="Route to human review and create a tracked request.",
        )

    action_map = {
        RequestKind.BUG: "Create a tracked fix request and search for existing work.",
        RequestKind.FEATURE: "Add to backlog and check for duplicates.",
        RequestKind.QUESTION: "Search knowledge base first; escalate if unanswered.",
        RequestKind.STUCK: "Diagnose merge/PR blockers and suggest next step.",
    }

    return Classification(
        kind=best_kind,
        confidence=best_score,
        summary=text[:120],
        suggested_action=action_map.get(best_kind, "Create tracked request."),
    )


def _score(text: str, patterns: list[str]) -> float:
    hits = sum(1 for p in patterns if re.search(p, text))
    return min(1.0, hits / max(1, len(patterns)))
