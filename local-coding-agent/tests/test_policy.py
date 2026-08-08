"""Tests for policy engine (SLICE 7).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import pytest

from local_agent.policy import PolicyDecision, PolicyEngine


@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine(network_enabled=False, plugin_enabled=False)


def test_read_tools_allowed(engine: PolicyEngine) -> None:
    for tool in ("list_files", "read_file", "search_files", "git_status"):
        decision = engine.authorize(tool)
        assert decision.allowed, f"{tool} should be allowed"
        assert decision.reason == "authorized"


def test_write_tools_allowed(engine: PolicyEngine) -> None:
    for tool in ("write_file", "edit_file"):
        decision = engine.authorize(tool)
        assert decision.allowed


def test_shell_exec_denied(engine: PolicyEngine) -> None:
    decision = engine.authorize("shell_exec")
    assert not decision.allowed
    assert decision.required_approval


def test_fetch_url_denied_by_default(engine: PolicyEngine) -> None:
    decision = engine.authorize("fetch_url")
    assert not decision.allowed
    assert "network" in decision.reason


def test_fetch_url_allowed_when_network_enabled() -> None:
    engine = PolicyEngine(network_enabled=True)
    decision = engine.authorize("fetch_url", user_approved=True)
    assert decision.allowed


def test_unknown_tool_denied(engine: PolicyEngine) -> None:
    decision = engine.authorize("arbitrary_shell")
    assert not decision.allowed
    assert "unknown tool" in decision.reason


def test_spawn_plugin_denied(engine: PolicyEngine) -> None:
    decision = engine.authorize("spawn_plugin")
    assert not decision.allowed
    assert "plugins disabled" in decision.reason


def test_spawn_plugin_with_flag() -> None:
    engine = PolicyEngine(plugin_enabled=True)
    decision = engine.authorize("spawn_plugin", user_approved=True)
    assert decision.allowed


def test_run_tests_allowed(engine: PolicyEngine) -> None:
    decision = engine.authorize("run_tests")
    assert decision.allowed


def test_policy_decision_structure(engine: PolicyEngine) -> None:
    decision = engine.authorize("read_file")
    assert isinstance(decision, PolicyDecision)
    assert "read:workspace" in decision.capability_scope


def test_approval_queue(engine: PolicyEngine) -> None:
    engine.approve_tool("shell_exec")
    assert "shell_exec" in engine.approved_tools
