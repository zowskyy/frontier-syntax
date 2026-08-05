"""Auto-generated scrub validation for deploy__config.yaml."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "deploy__config.yaml"


def test_deploy__config_yaml_exists():
    assert SOURCE.exists()
    assert SOURCE.read_text(encoding="utf-8").strip()
