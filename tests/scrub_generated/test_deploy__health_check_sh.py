"""Auto-generated scrub validation for deploy__health_check.sh."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "deploy__health_check.sh"


def test_deploy__health_check_sh_exists():
    assert SOURCE.exists()
    assert SOURCE.read_text(encoding="utf-8").strip()
