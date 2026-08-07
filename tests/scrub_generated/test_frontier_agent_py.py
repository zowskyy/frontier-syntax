"""Auto-generated scrub validation for frontier_agent.py."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "frontier_agent.py"


def test_frontier_agent_py_syntax():
    """Verify extracted Python file compiles."""
    assert SOURCE.exists(), f"missing extracted file: {SOURCE}"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SOURCE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
