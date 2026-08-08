"""Tests for transactional edit engine (SLICE 8).

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.edit_engine import EditEngine, EditOperation, EditOperationKind, file_hash


@pytest.fixture
def engine(sample_project: Path) -> EditEngine:
    return EditEngine(sample_project)


def test_search_replace_commit(engine: EditEngine, sample_project: Path) -> None:
    original = (sample_project / "hello.py").read_text(encoding="utf-8")
    expected = file_hash(original)
    ops = [EditOperation(
        kind=EditOperationKind.SEARCH_REPLACE,
        old_string="world",
        new_string="universe",
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash=expected)
    assert result.success
    assert result.before_hash == expected
    assert result.after_hash != expected
    updated = (sample_project / "hello.py").read_text(encoding="utf-8")
    assert "universe" in updated


def test_stale_hash_rejected(engine: EditEngine) -> None:
    ops = [EditOperation(
        kind=EditOperationKind.SEARCH_REPLACE,
        old_string="world",
        new_string="universe",
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash="deadbeef" * 8)
    assert not result.success
    assert "stale context" in (result.error or "")


def test_syntax_failure_rollback(engine: EditEngine, sample_project: Path) -> None:
    original = (sample_project / "hello.py").read_text(encoding="utf-8")
    expected = file_hash(original)
    ops = [EditOperation(
        kind=EditOperationKind.SEARCH_REPLACE,
        old_string='"""Return a greeting."""',
        new_string="def broken(:\n",
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash=expected)
    assert not result.success
    assert "syntax" in (result.error or "").lower()
    current = (sample_project / "hello.py").read_text(encoding="utf-8")
    assert current == original


def test_insert_operation(engine: EditEngine, sample_project: Path) -> None:
    original = (sample_project / "hello.py").read_text(encoding="utf-8")
    expected = file_hash(original)
    ops = [EditOperation(
        kind=EditOperationKind.INSERT,
        new_string="# header\n",
        offset=0,
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash=expected, check_syntax=False)
    assert result.success
    updated = (sample_project / "hello.py").read_text(encoding="utf-8")
    assert updated.startswith("# header\n")


def test_delete_operation(engine: EditEngine, sample_project: Path) -> None:
    original = (sample_project / "hello.py").read_text(encoding="utf-8")
    expected = file_hash(original)
    idx = original.index('"""Return a greeting."""')
    ops = [EditOperation(
        kind=EditOperationKind.DELETE,
        offset=idx,
        length=len('"""Return a greeting."""'),
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash=expected, check_syntax=False)
    assert result.success


def test_search_not_found(engine: EditEngine, sample_project: Path) -> None:
    original = (sample_project / "hello.py").read_text(encoding="utf-8")
    expected = file_hash(original)
    ops = [EditOperation(
        kind=EditOperationKind.SEARCH_REPLACE,
        old_string="NONEXISTENT_STRING",
        new_string="x",
    )]
    result = engine.commit_edit("hello.py", ops, expected_hash=expected)
    assert not result.success
    current = (sample_project / "hello.py").read_text(encoding="utf-8")
    assert current == original


def test_file_hash_deterministic() -> None:
    assert file_hash("hello") == file_hash("hello")
    assert file_hash("hello") != file_hash("world")


def test_new_file_commit(engine: EditEngine, sample_project: Path) -> None:
    ops = [EditOperation(
        kind=EditOperationKind.INSERT,
        new_string="y = 2\n",
        offset=0,
    )]
    result = engine.commit_edit("new_module.py", ops, check_syntax=False)
    assert result.success
    assert (sample_project / "new_module.py").exists()
