"""Tests for core agent loop (SLICE 17)."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.agent.loop import AgentLoop, AgentTimeoutError
from local_agent.model.mock import MockProvider
from local_agent.policy import PolicyEngine
from local_agent.tools.handlers import ToolContext, create_default_registry
from local_agent.types import AgentState


def test_agent_loop_completes_simple_task(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task")
    loop = AgentLoop(
        provider=provider,
        workspace_root=workspace_tmp,
        policy=PolicyEngine(),
        tools=create_default_registry(),
    )
    result = loop.run("list files in workspace")
    assert result.final_state == AgentState.COMPLETE
    assert "successfully" in result.message.lower()
    assert len(result.observations) == 1
    assert result.observations[0].success
    assert result.observations[0].tool == "list_files"


def test_agent_loop_state_progression(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task")
    loop = AgentLoop(provider=provider, workspace_root=workspace_tmp)
    result = loop.run("list files")
    assert result.steps_executed >= 7
    assert result.elapsed_ms >= 0


def test_agent_loop_fails_on_invalid_output(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="invalid_output")
    loop = AgentLoop(provider=provider, workspace_root=workspace_tmp)
    result = loop.run("bad task")
    assert result.final_state == AgentState.FAILED


def test_agent_loop_policy_denial(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task")
    policy = PolicyEngine(policy_table={})
    loop = AgentLoop(provider=provider, workspace_root=workspace_tmp, policy=policy)
    result = loop.run("list files")
    assert result.final_state == AgentState.FAILED
    assert "denied" in result.message.lower() or "deny" in result.message.lower()


def test_agent_loop_cancellation(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task")
    loop = AgentLoop(provider=provider, workspace_root=workspace_tmp)
    loop.cancel()
    result = loop.run("list files")
    assert result.final_state == AgentState.CANCELLED


def test_agent_loop_timeout(fixtures_dir: Path, workspace_tmp: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task", generate_delay=0.05)
    loop = AgentLoop(provider=provider, workspace_root=workspace_tmp, timeout_seconds=0.001)
    with pytest.raises(AgentTimeoutError):
        loop.run("list files")


def test_mock_provider_fixture_health(fixtures_dir: Path) -> None:
    provider = MockProvider(fixtures_dir=fixtures_dir, scenario="simple_task")
    health = provider.health()
    assert health["status"] == "ok"
    assert health["provider"] == "mock"
