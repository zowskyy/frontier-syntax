"""Workspace filesystem security boundary.

Licensed under SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
log = logger

PROTECTED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\.env($|\.)"),
    re.compile(r"^credentials", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"^\.git/config$"),
    re.compile(r"^\.git/hooks/"),
)


class WorkspaceError(PermissionError):
    """Raised when a workspace operation is denied."""


class WorkspaceGuard:
    """Filesystem boundary for all agent file operations."""

    def __init__(self, workspace_root: Path, max_file_size: int = 1_048_576) -> None:
        self.workspace_root = workspace_root.resolve()
        self.max_file_size = max_file_size

    def resolve_workspace_path(self, relative_path: str | Path) -> Path:
        """Resolve a relative path to an absolute path within the workspace."""
        raw = str(relative_path).strip()
        if not raw:
            raise WorkspaceError("empty path not allowed")

        decoded = urllib.parse.unquote(raw)
        if ".." in Path(decoded).parts:
            raise WorkspaceError(f"path traversal rejected: {relative_path}")

        candidate = (self.workspace_root / decoded).resolve()

        if not self._is_within_workspace(candidate):
            raise WorkspaceError(f"path escapes workspace: {relative_path}")

        if candidate.is_symlink():
            real = candidate.resolve()
            if not self._is_within_workspace(real):
                raise WorkspaceError(f"symlink escapes workspace: {relative_path}")

        return candidate

    def is_allowed_path(self, path: Path) -> bool:
        """Return True if path is within workspace and not protected."""
        try:
            resolved = path.resolve()
            if not self._is_within_workspace(resolved):
                return False
            return not self.is_protected_path(resolved)
        except (OSError, ValueError):
            return False

    def is_protected_path(self, path: Path) -> bool:
        """Return True if path matches protected deny-list patterns."""
        try:
            rel = path.resolve().relative_to(self.workspace_root)
        except ValueError:
            return True
        rel_str = rel.as_posix()
        return any(pattern.search(rel_str) for pattern in PROTECTED_PATTERNS)

    def read_file(self, relative_path: str | Path) -> str:
        """Read file contents within workspace boundary."""
        path = self.resolve_workspace_path(relative_path)
        if self.is_protected_path(path):
            log.warning("denied read of protected path: %s", path)
            raise WorkspaceError(f"protected path denied: {relative_path}")
        if not path.is_file():
            raise FileNotFoundError(f"file not found: {relative_path}")
        size = path.stat().st_size
        if size > self.max_file_size:
            raise WorkspaceError(f"file exceeds max size ({size} > {self.max_file_size})")
        return path.read_text(encoding="utf-8")

    def write_file(self, relative_path: str | Path, content: str) -> None:
        """Write file contents within workspace boundary."""
        path = self.resolve_workspace_path(relative_path)
        if self.is_protected_path(path):
            log.warning("denied write to protected path: %s", path)
            raise WorkspaceError(f"protected path denied: {relative_path}")
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_file_size:
            raise WorkspaceError("content exceeds max file size")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_file(self, relative_path: str | Path) -> None:
        """Delete file within workspace boundary."""
        path = self.resolve_workspace_path(relative_path)
        if self.is_protected_path(path):
            log.warning("denied delete of protected path: %s", path)
            raise WorkspaceError(f"protected path denied: {relative_path}")
        if not path.is_file():
            raise FileNotFoundError(f"file not found: {relative_path}")
        path.unlink()

    def _is_within_workspace(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.workspace_root)
            return True
        except ValueError:
            return False


def resolve_workspace_path(workspace_root: Path, relative_path: str | Path) -> Path:
    """Module-level helper wrapping WorkspaceGuard.resolve_workspace_path."""
    return WorkspaceGuard(workspace_root).resolve_workspace_path(relative_path)


def is_allowed_path(workspace_root: Path, path: Path) -> bool:
    return WorkspaceGuard(workspace_root).is_allowed_path(path)


def is_protected_path(workspace_root: Path, path: Path) -> bool:
    return WorkspaceGuard(workspace_root).is_protected_path(path)


def read_file(workspace_root: Path, relative_path: str | Path, max_file_size: int = 1_048_576) -> str:
    return WorkspaceGuard(workspace_root, max_file_size).read_file(relative_path)


def write_file(
    workspace_root: Path,
    relative_path: str | Path,
    content: str,
    max_file_size: int = 1_048_576,
) -> None:
    WorkspaceGuard(workspace_root, max_file_size).write_file(relative_path, content)


def delete_file(workspace_root: Path, relative_path: str | Path) -> None:
    WorkspaceGuard(workspace_root).delete_file(relative_path)
