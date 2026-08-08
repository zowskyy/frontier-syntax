"""Edit operation types, handlers, and transactional commit.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from local_agent.workspace import WorkspaceGuard

logger = logging.getLogger(__name__)
log = logger


class EditOperationKind(str, Enum):
    SEARCH_REPLACE = "SEARCH_REPLACE"
    INSERT = "INSERT"
    DELETE = "DELETE"


@dataclass
class EditOperation:
    kind: EditOperationKind
    old_string: str = ""
    new_string: str = ""
    offset: int = 0
    length: int = 0


@dataclass
class EditResult:
    success: bool
    path: str
    before_hash: str = ""
    after_hash: str = ""
    error: Optional[str] = None


def file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _syntax_check_python(content: str) -> Optional[str]:
    import ast

    try:
        ast.parse(content)
        return None
    except SyntaxError as exc:
        return str(exc)


def _apply_search_replace(content: str, op: EditOperation) -> str:
    if op.old_string not in content:
        raise ValueError(f"search string not found: {op.old_string!r}")
    return content.replace(op.old_string, op.new_string, 1)


def _apply_insert(content: str, op: EditOperation) -> str:
    return content[: op.offset] + op.new_string + content[op.offset :]


def _apply_delete(content: str, op: EditOperation) -> str:
    return content[: op.offset] + content[op.offset + op.length :]


_HANDLERS = {
    EditOperationKind.SEARCH_REPLACE: _apply_search_replace,
    EditOperationKind.INSERT: _apply_insert,
    EditOperationKind.DELETE: _apply_delete,
}


def apply_operation(content: str, op: EditOperation) -> str:
    handler = _HANDLERS.get(op.kind)
    if handler is None:
        raise ValueError(f"unknown operation kind: {op.kind}")
    return handler(content, op)


def apply_operations(content: str, operations: list[EditOperation]) -> str:
    result = content
    for op in operations:
        result = apply_operation(result, op)
    return result


def _atomic_write(path: Path, content: str) -> Optional[str]:
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".edit_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content.encode("utf-8"))
        os.replace(tmp_name, str(path))
        return None
    except Exception as exc:
        Path(tmp_name).unlink(missing_ok=True)
        return str(exc)


def commit_transaction(
    guard: WorkspaceGuard,
    relative_path: str,
    operations: list[EditOperation],
    expected_hash: Optional[str] = None,
    check_syntax: bool = True,
    syntax_checker: Optional[Callable[[str], Optional[str]]] = None,
) -> EditResult:
    checker = syntax_checker or _syntax_check_python
    path = guard.resolve_workspace_path(relative_path)
    original = guard.read_file(relative_path) if path.exists() else ""
    before_hash = file_hash(original)

    stale = expected_hash is not None and before_hash != expected_hash
    if stale:
        return EditResult(False, relative_path, before_hash, error="stale context: file hash mismatch")

    try:
        updated = apply_operations(original, operations)
    except ValueError as exc:
        return EditResult(False, relative_path, before_hash, error=str(exc))

    needs_syntax = check_syntax and relative_path.endswith(".py")
    syntax_error = checker(updated) if needs_syntax else None
    if syntax_error:
        return EditResult(False, relative_path, before_hash, error=f"syntax check failed: {syntax_error}")

    write_error = _atomic_write(path, updated)
    if write_error:
        return EditResult(False, relative_path, before_hash, error=f"commit failed: {write_error}")

    after_hash = file_hash(updated)
    log.info("committed edit %s before=%s after=%s", relative_path, before_hash[:8], after_hash[:8])
    return EditResult(True, relative_path, before_hash, after_hash)


def rollback_transaction(
    guard: WorkspaceGuard,
    relative_path: str,
    original_content: str,
    expected_hash: str,
) -> EditResult:
    path = guard.resolve_workspace_path(relative_path)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    current_hash = file_hash(current)
    if current_hash != expected_hash:
        return EditResult(False, relative_path, error="cannot rollback: file changed since edit")
    guard.write_file(relative_path, original_content)
    return EditResult(True, relative_path, current_hash, file_hash(original_content))
