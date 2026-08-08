"""Tests for structured output parsing (SLICE 5).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json

import pytest

from local_agent.output import (
    ResponseType,
    parse_clarification,
    parse_edit_request,
    parse_error_recovery,
    parse_final,
    parse_model_output,
    parse_tool_call,
)


def test_parse_final() -> None:
    text = json.dumps({"type": "FINAL", "content": "Task complete."})
    result = parse_model_output(text)
    assert result.valid
    assert result.response_type == ResponseType.FINAL
    assert result.data["content"] == "Task complete."


def test_parse_tool_call() -> None:
    text = json.dumps({
        "type": "TOOL_CALL",
        "tool": "read_file",
        "arguments": {"path": "hello.py"},
    })
    result = parse_tool_call(text)
    assert result.valid
    assert result.response_type == ResponseType.TOOL_CALL


def test_parse_edit_request() -> None:
    text = json.dumps({
        "type": "EDIT_REQUEST",
        "path": "hello.py",
        "operations": [{"kind": "SEARCH_REPLACE", "old": "a", "new": "b"}],
    })
    result = parse_edit_request(text)
    assert result.valid
    assert result.data["path"] == "hello.py"


def test_parse_clarification() -> None:
    text = json.dumps({"type": "CLARIFICATION", "question": "Which file?"})
    result = parse_clarification(text)
    assert result.valid
    assert result.data["question"] == "Which file?"


def test_parse_error_recovery() -> None:
    text = json.dumps({"type": "ERROR_RECOVERY", "message": "retry needed"})
    result = parse_error_recovery(text)
    assert result.valid


def test_malformed_json_rejected() -> None:
    result = parse_model_output("{invalid json")
    assert not result.valid
    assert result.response_type == ResponseType.ERROR_RECOVERY


def test_truncated_json_rejected() -> None:
    result = parse_model_output('{"type": "FINAL", "cont')
    assert not result.valid


def test_unknown_type_rejected() -> None:
    result = parse_model_output(json.dumps({"type": "UNKNOWN", "data": 1}))
    assert not result.valid


def test_missing_required_field() -> None:
    result = parse_model_output(json.dumps({"type": "FINAL"}))
    assert not result.valid
    assert "content" in (result.error or "")


def test_json_in_code_block() -> None:
    text = 'Here is the result:\n```json\n{"type": "FINAL", "content": "done"}\n```'
    result = parse_final(text)
    assert result.valid
    assert result.data["content"] == "done"


def test_no_json_found() -> None:
    result = parse_model_output("just plain text")
    assert not result.valid
