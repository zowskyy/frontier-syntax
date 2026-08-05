"""Auto-generated scrub validation for src__compiler__proof_generator.rs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "src__compiler__proof_generator.rs"


def test_src__compiler__proof_generator_rs_exists():
    """Verify extracted Rust file still exists and is non-empty."""
    assert SOURCE.exists(), f"missing extracted file: {SOURCE}"
    assert SOURCE.stat().st_size > 0
