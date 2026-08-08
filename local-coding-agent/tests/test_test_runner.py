import os
import subprocess
import time

import pytest

from local_agent.test_runner import (
    DEFAULT_ALLOWLIST,
    TestRunner,
    TestRunnerError,
)


def test_allowlisted_command_runs_successfully(tmp_path):
    runner = TestRunner(timeout_seconds=10)
    script = tmp_path / "ok.py"
    script.write_text("print('hello-tests')\n", encoding="utf-8")
    result = runner.run("python", f"python3 {script}", str(tmp_path))
    assert result.exit_code == 0
    assert "hello-tests" in result.stdout
    assert not result.timed_out


def test_rejects_non_allowlisted_command(tmp_path):
    runner = TestRunner()
    with pytest.raises(TestRunnerError):
        runner.run("python", "rm -rf /", str(tmp_path))


def test_timeout_kills_process(tmp_path):
    runner = TestRunner(timeout_seconds=1, grace_seconds=0.2)
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    start = time.monotonic()
    result = runner.run("python", f"python3 {script}", str(tmp_path))
    elapsed = time.monotonic() - start
    assert result.timed_out
    assert result.exit_code == 124
    assert elapsed < 4


def test_output_limits_applied(tmp_path):
    runner = TestRunner(timeout_seconds=10, max_output_bytes=128)
    script = tmp_path / "chatty.py"
    script.write_text("print('x' * 5000)\n", encoding="utf-8")
    result = runner.run("python", f"python3 {script}", str(tmp_path))
    assert len(result.stdout.encode("utf-8")) <= 128
    assert result.stdout_truncated


def test_javascript_allowlist_contains_npm_test():
    assert "npm test" in DEFAULT_ALLOWLIST["javascript"]
