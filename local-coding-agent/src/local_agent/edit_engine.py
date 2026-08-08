"""Transactional edit engine with hash verification.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

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
  """Basic Python syntax check."""
  import ast

  try:
    ast.parse(content)
    return None
  except SyntaxError as exc:
    return str(exc)


class EditEngine:
    """Hash-checked transactional edits with atomic commit."""

    def __init__(
        self,
        workspace_root: Path,
        max_file_size: int = 1_048_576,
        syntax_checker: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self.guard = WorkspaceGuard(workspace_root, max_file_size)
        self.syntax_checker = syntax_checker or _syntax_check_python

    def apply_operations(self, content: str, operations: list[EditOperation]) -> str:
        result = content
        for op in operations:
            if op.kind == EditOperationKind.SEARCH_REPLACE:
                if op.old_string not in result:
                    raise ValueError(f"search string not found: {op.old_string!r}")
                result = result.replace(op.old_string, op.new_string, 1)
            elif op.kind == EditOperationKind.INSERT:
                result = result[: op.offset] + op.new_string + result[op.offset :]
            elif op.kind == EditOperationKind.DELETE:
                result = result[: op.offset] + result[op.offset + op.length :]
            else:
                raise ValueError(f"unknown operation kind: {op.kind}")
        return result

    def commit_edit(
        self,
        relative_path: str,
        operations: list[EditOperation],
        expected_hash: Optional[str] = None,
        check_syntax: bool = True,
    ) -> EditResult:
        """Apply edits transactionally: hash check → temp copy → apply → syntax → atomic commit."""
        path = self.guard.resolve_workspace_path(relative_path)

        if not path.exists():
            original = ""
        else:
            original = self.guard.read_file(relative_path)

        before_hash = file_hash(original)

        if expected_hash is not None and before_hash != expected_hash:
            return EditResult(
                success=False,
                path=relative_path,
                before_hash=before_hash,
                error="stale context: file hash mismatch",
            )

        try:
            updated = self.apply_operations(original, operations)
        except ValueError as exc:
            return EditResult(
                success=False,
                path=relative_path,
                before_hash=before_hash,
                error=str(exc),
            )

        if check_syntax and relative_path.endswith(".py"):
            syntax_error = self.syntax_checker(updated)
            if syntax_error:
                return EditResult(
                    success=False,
                    path=relative_path,
                    before_hash=before_hash,
                    error=f"syntax check failed: {syntax_error}",
                )

        after_hash = file_hash(updated)

        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".edit_", suffix=".tmp"
        )
        try:
            os.write(fd, updated.encode("utf-8"))
            os.close(fd)
            fd = -1
            tmp_path = Path(tmp_name)
            os.replace(str(tmp_path), str(path))
        except Exception as exc:
            if fd >= 0:
                os.close(fd)
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()
            return EditResult(
                success=False,
                path=relative_path,
                before_hash=before_hash,
                error=f"commit failed: {exc}",
            )

        log.info("committed edit %s before=%s after=%s", relative_path, before_hash[:8], after_hash[:8])
        return EditResult(
            success=True,
            path=relative_path,
            before_hash=before_hash,
            after_hash=after_hash,
        )

    def rollback(self, relative_path: str, original_content: str, expected_hash: str) -> EditResult:
        """Rollback to original content if hash still matches."""
        path = self.guard.resolve_workspace_path(relative_path)
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        current_hash = file_hash(current)
        if current_hash != expected_hash:
            return EditResult(
                success=False,
                path=relative_path,
                error="cannot rollback: file changed since edit",
            )
        self.guard.write_file(relative_path, original_content)
        return EditResult(
            success=True,
            path=relative_path,
            before_hash=current_hash,
            after_hash=file_hash(original_content),
        )
