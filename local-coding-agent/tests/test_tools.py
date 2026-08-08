"""Tests for tool registry (SLICE 6).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.tools.handlers import ToolContext, create_default_registry
from local_agent.tools.registry import ToolRiskClass


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def ctx(sample_project: Path) -> ToolContext:
    return ToolContext(workspace_root=sample_project)


def test_all_tools_registered(registry) -> None:
    names = {t.name for t in registry.list_tools()}
    expected = {"list_files", "read_file", "search_files", "write_file", "edit_file", "run_tests", "git_status"}
    assert names == expected


def test_risk_classes(registry) -> None:
    read_tools = registry.list_by_risk(ToolRiskClass.READ_ONLY)
    assert len(read_tools) == 4
    mutating = registry.list_by_risk(ToolRiskClass.MUTATING_APPROVAL)
    assert len(mutating) == 2
    high = registry.list_by_risk(ToolRiskClass.HIGH_RISK)
    assert len(high) == 1
    assert high[0].name == "run_tests"


def test_list_files(registry, ctx: ToolContext) -> None:
    result = registry.execute("list_files", {}, ctx)
    assert result["success"]
    assert "hello.py" in result["files"]


def test_read_file(registry, ctx: ToolContext) -> None:
    result = registry.execute("read_file", {"path": "hello.py"}, ctx)
    assert result["success"]
    assert "greet" in result["content"]


def test_search_files(registry, ctx: ToolContext) -> None:
    result = registry.execute("search_files", {"query": "greet"}, ctx)
    assert result["success"]
    assert len(result["matches"]) >= 1


def test_write_file(registry, ctx: ToolContext) -> None:
    result = registry.execute("write_file", {"path": "out.py", "content": "x=1\n"}, ctx)
    assert result["success"]
    read = registry.execute("read_file", {"path": "out.py"}, ctx)
    assert read["content"] == "x=1\n"


def test_edit_file(registry, ctx: ToolContext) -> None:
    result = registry.execute("edit_file", {
        "path": "hello.py",
        "old_string": "world",
        "new_string": "universe",
    }, ctx)
    assert result["success"]
    assert result["edited"]


def test_run_tests_allowlist(registry, ctx: ToolContext) -> None:
    result = registry.execute("run_tests", {"command": "rm -rf /"}, ctx)
    assert not result.get("success", True) or "error" in result


def test_run_tests_pytest(registry, ctx: ToolContext) -> None:
    result = registry.execute("run_tests", {"command": "pytest"}, ctx)
    assert "exit_code" in result


def test_unknown_tool(registry, ctx: ToolContext) -> None:
    result = registry.execute("shell_exec", {"cmd": "ls"}, ctx)
    assert not result["success"]


def test_policy_table(registry) -> None:
    table = registry.to_policy_table()
    assert len(table) == 7
    assert all("risk_class" in entry for entry in table)
