"""SLICE 9 — Safe test execution with allowlist, timeout, and output limits."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Mapping, Sequence

DEFAULT_ALLOWLIST: Mapping[str, tuple[str, ...]] = {
    "python": ("pytest", "python -m pytest", "python -m unittest"),
    "javascript": ("npm test", "npm run test", "yarn test", "pnpm test"),
    "rust": ("cargo test",),
    "go": ("go test ./...",),
}

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024
TIMEOUT_GRACE_SECONDS = 2


@dataclass(frozen=True)
class TestRunResult:
    """Outcome of a single test invocation."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    stdout_truncated: bool
    stderr_truncated: bool
    command: str


class TestRunnerError(ValueError):
    """Raised when a test command is not allowlisted."""


def _normalize_command(command: str) -> str:
    return " ".join(command.strip().split())


def _is_allowlisted(project_type: str, command: str, allowlist: Mapping[str, Sequence[str]]) -> bool:
    normalized = _normalize_command(command)
    allowed = allowlist.get(project_type, ())
    if any(
        normalized == _normalize_command(entry)
        or normalized.startswith(_normalize_command(entry) + " ")
        for entry in allowed
    ):
        return True
    if project_type == "python" and normalized.startswith(("python ", "python3 ")):
        target = normalized.split(maxsplit=1)[1]
        return target.endswith(".py")
    return False


def _truncate_output(data: bytes, max_bytes: int) -> tuple[str, bool]:
    if len(data) <= max_bytes:
        return data.decode("utf-8", errors="replace"), False
    return data[:max_bytes].decode("utf-8", errors="replace"), True


def _kill_process_tree(pid: int) -> None:
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _read_limited(pipe, max_bytes: int) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    total = 0
    truncated = False
    while True:
        piece = pipe.read(4096)
        if not piece:
            break
        remaining = max_bytes - total
        if remaining <= 0:
            truncated = True
            break
        if len(piece) > remaining:
            chunks.append(piece[:remaining])
            truncated = True
            break
        chunks.append(piece)
        total += len(piece)
    return b"".join(chunks), truncated


class TestRunner:
    """Execute project tests with deterministic safety boundaries."""

    def __init__(
        self,
        allowlist: Mapping[str, Sequence[str]] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
        grace_seconds: float = TIMEOUT_GRACE_SECONDS,
    ) -> None:
        self.allowlist = dict(allowlist or DEFAULT_ALLOWLIST)
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.grace_seconds = grace_seconds

    def validate_command(self, project_type: str, command: str) -> None:
        if not _is_allowlisted(project_type, command, self.allowlist):
            raise TestRunnerError(
                f"Command not allowlisted for project type '{project_type}': {command!r}"
            )

    def run(self, project_type: str, command: str, cwd: str) -> TestRunResult:
        self.validate_command(project_type, command)
        normalized = _normalize_command(command)

        process = subprocess.Popen(
            normalized,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            preexec_fn=os.setsid,
        )

        deadline = time.monotonic() + self.timeout_seconds
        timed_out = False

        while process.poll() is None:
            if time.monotonic() >= deadline:
                timed_out = True
                _kill_process_tree(process.pid)
                time.sleep(self.grace_seconds)
                if process.poll() is None:
                    _kill_process_tree(process.pid)
                break
            time.sleep(0.05)

        stdout_bytes, stdout_truncated = _read_limited(process.stdout, self.max_output_bytes)
        stderr_bytes, stderr_truncated = _read_limited(process.stderr, self.max_output_bytes)
        process.stdout.close()
        process.stderr.close()

        exit_code = process.wait(timeout=5) if process.poll() is None else process.returncode
        if timed_out:
            exit_code = 124

        stdout, extra_stdout_trunc = _truncate_output(stdout_bytes, self.max_output_bytes)
        stderr, extra_stderr_trunc = _truncate_output(stderr_bytes, self.max_output_bytes)

        return TestRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            stdout_truncated=stdout_truncated or extra_stdout_trunc,
            stderr_truncated=stderr_truncated or extra_stderr_trunc,
            command=normalized,
        )
