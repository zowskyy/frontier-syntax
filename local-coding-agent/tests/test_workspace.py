"""Tests for workspace guard (SLICE 2).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from local_agent.workspace import WorkspaceError, WorkspaceGuard


@pytest.fixture
def guard(sample_project: Path) -> WorkspaceGuard:
    return WorkspaceGuard(sample_project)


def test_resolve_valid_path(guard: WorkspaceGuard) -> None:
    path = guard.resolve_workspace_path("hello.py")
    assert path.name == "hello.py"
    assert path.is_file()


def test_path_traversal_rejected(guard: WorkspaceGuard) -> None:
    with pytest.raises(WorkspaceError, match="traversal"):
        guard.resolve_workspace_path("../outside.txt")


def test_encoded_traversal_rejected(guard: WorkspaceGuard) -> None:
    with pytest.raises(WorkspaceError):
        guard.resolve_workspace_path("..%2F..%2Fetc%2Fpasswd")


def test_symlink_escape_rejected(sample_project: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    link = sample_project / "escape_link"
    link.symlink_to(outside)
    guard = WorkspaceGuard(sample_project)
    with pytest.raises(WorkspaceError, match="escapes workspace|symlink"):
        guard.resolve_workspace_path("escape_link")


def test_protected_env_file(sample_project: Path) -> None:
    env_file = sample_project / ".env"
    env_file.write_text("SECRET=abc")
    guard = WorkspaceGuard(sample_project)
    assert guard.is_protected_path(env_file)
    with pytest.raises(WorkspaceError, match="protected"):
        guard.read_file(".env")


def test_protected_git_config(sample_project: Path) -> None:
    git_config = sample_project / ".git" / "config"
    git_config.parent.mkdir(parents=True, exist_ok=True)
    git_config.write_text("[core]")
    guard = WorkspaceGuard(sample_project)
    assert guard.is_protected_path(git_config)


def test_read_write_delete(guard: WorkspaceGuard) -> None:
    content = guard.read_file("hello.py")
    assert "greet" in content
    guard.write_file("new_file.py", "x = 1\n")
    assert guard.read_file("new_file.py") == "x = 1\n"
    guard.delete_file("new_file.py")
    with pytest.raises(FileNotFoundError):
        guard.read_file("new_file.py")


def test_is_allowed_path(guard: WorkspaceGuard, sample_project: Path) -> None:
    hello = sample_project / "hello.py"
    assert guard.is_allowed_path(hello)
    env = sample_project / ".env"
    env.write_text("KEY=val")
    assert not guard.is_allowed_path(env)


def test_max_file_size_rejected(guard: WorkspaceGuard) -> None:
    small_guard = WorkspaceGuard(guard.workspace_root, max_file_size=10)
    with pytest.raises(WorkspaceError, match="max size"):
        small_guard.read_file("hello.py")
