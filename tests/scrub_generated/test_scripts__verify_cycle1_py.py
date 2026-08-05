"""Auto-generated scrub validation for scripts__verify_cycle1.py."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "scripts__verify_cycle1.py"


def test_scripts__verify_cycle1_py_syntax():
    """Verify extracted Python file compiles."""
    assert SOURCE.exists(), f"missing extracted file: {SOURCE}"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SOURCE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
