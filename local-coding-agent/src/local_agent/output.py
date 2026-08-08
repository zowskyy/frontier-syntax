"""Structured model output parsing.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)
log = logger


class ResponseType(str, Enum):
    FINAL = "FINAL"
    TOOL_CALL = "TOOL_CALL"
    EDIT_REQUEST = "EDIT_REQUEST"
    CLARIFICATION = "CLARIFICATION"
    ERROR_RECOVERY = "ERROR_RECOVERY"


@dataclass
class ParsedResponse:
    response_type: ResponseType
    data: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    valid: bool = True
    error: Optional[str] = None


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> Optional[str]:
    text = text.strip()
    if text.startswith("{"):
        return text
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1)
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return None


def _validate_payload(response_type: ResponseType, data: dict[str, Any]) -> Optional[str]:
    if response_type == ResponseType.FINAL:
        if "content" not in data:
            return "FINAL requires 'content' field"
    elif response_type == ResponseType.TOOL_CALL:
        if "tool" not in data or "arguments" not in data:
            return "TOOL_CALL requires 'tool' and 'arguments' fields"
    elif response_type == ResponseType.EDIT_REQUEST:
        if "path" not in data or "operations" not in data:
            return "EDIT_REQUEST requires 'path' and 'operations' fields"
    elif response_type == ResponseType.CLARIFICATION:
        if "question" not in data:
            return "CLARIFICATION requires 'question' field"
    elif response_type == ResponseType.ERROR_RECOVERY:
        if "message" not in data:
            return "ERROR_RECOVERY requires 'message' field"
    return None


def parse_model_output(text: str) -> ParsedResponse:
    """Parse structured model output from JSON text.

    Invalid output returns a ParsedResponse with valid=False and error message.
    Malformed JSON never directly executes tools or edits.
    """
    raw = text
    json_str = _extract_json(text)
    if json_str is None:
        return ParsedResponse(
            response_type=ResponseType.ERROR_RECOVERY,
            data={"message": "no JSON found in model output"},
            raw=raw,
            valid=False,
            error="no JSON found",
        )

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return ParsedResponse(
            response_type=ResponseType.ERROR_RECOVERY,
            data={"message": f"malformed JSON: {exc}"},
            raw=raw,
            valid=False,
            error=str(exc),
        )

    if not isinstance(data, dict):
        return ParsedResponse(
            response_type=ResponseType.ERROR_RECOVERY,
            data={"message": "expected JSON object"},
            raw=raw,
            valid=False,
            error="expected JSON object",
        )

    type_str = data.get("type", "")
    try:
        response_type = ResponseType(type_str)
    except ValueError:
        return ParsedResponse(
            response_type=ResponseType.ERROR_RECOVERY,
            data={"message": f"unknown response type: {type_str}"},
            raw=raw,
            valid=False,
            error=f"unknown type: {type_str}",
        )

    validation_error = _validate_payload(response_type, data)
    if validation_error:
        return ParsedResponse(
            response_type=ResponseType.ERROR_RECOVERY,
            data={"message": validation_error},
            raw=raw,
            valid=False,
            error=validation_error,
        )

    return ParsedResponse(
        response_type=response_type,
        data=data,
        raw=raw,
        valid=True,
    )


def parse_final(text: str) -> ParsedResponse:
    return parse_model_output(text)


def parse_tool_call(text: str) -> ParsedResponse:
    result = parse_model_output(text)
    if result.valid and result.response_type != ResponseType.TOOL_CALL:
        result.valid = False
        result.error = f"expected TOOL_CALL, got {result.response_type.value}"
    return result


def parse_edit_request(text: str) -> ParsedResponse:
    result = parse_model_output(text)
    if result.valid and result.response_type != ResponseType.EDIT_REQUEST:
        result.valid = False
        result.error = f"expected EDIT_REQUEST, got {result.response_type.value}"
    return result


def parse_clarification(text: str) -> ParsedResponse:
    result = parse_model_output(text)
    if result.valid and result.response_type != ResponseType.CLARIFICATION:
        result.valid = False
        result.error = f"expected CLARIFICATION, got {result.response_type.value}"
    return result


def parse_error_recovery(text: str) -> ParsedResponse:
    result = parse_model_output(text)
    if result.valid and result.response_type != ResponseType.ERROR_RECOVERY:
        result.valid = False
        result.error = f"expected ERROR_RECOVERY, got {result.response_type.value}"
    return result
