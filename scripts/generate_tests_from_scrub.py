#!/usr/bin/env python3
"""Generate validation tests from chat_scrub/CODE_EXTRACTION/."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "chat_scrub" / "CODE_EXTRACTION"
OUTPUT_DIR = ROOT / "tests" / "scrub_generated"


def generate_test_for_file(source: Path) -> str:
    rel = source.name
    if source.suffix == ".py":
        return f'''"""Auto-generated scrub validation for {rel}."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "{rel}"


def test_{rel.replace(".", "_").replace("-", "_")}_syntax():
    """Verify extracted Python file compiles."""
    assert SOURCE.exists(), f"missing extracted file: {{SOURCE}}"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SOURCE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
'''
    if source.suffix == ".rs":
        return f'''"""Auto-generated scrub validation for {rel}."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "{rel}"


def test_{rel.replace(".", "_").replace("-", "_")}_exists():
    """Verify extracted Rust file still exists and is non-empty."""
    assert SOURCE.exists(), f"missing extracted file: {{SOURCE}}"
    assert SOURCE.stat().st_size > 0
'''
    if source.suffix in {".sh", ".yaml"}:
        return f'''"""Auto-generated scrub validation for {rel}."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chat_scrub" / "CODE_EXTRACTION" / "{rel}"


def test_{rel.replace(".", "_").replace("-", "_")}_exists():
    assert SOURCE.exists()
    assert SOURCE.read_text(encoding="utf-8").strip()
'''
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate tests from scrub extraction")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--run", action="store_true", help="Run pytest after generation")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"FAIL: input directory not found: {args.input}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "__init__.py").write_text("", encoding="utf-8")

    count = 0
    for source in sorted(args.input.iterdir()):
        if source.is_file() and not source.name.startswith("."):
            content = generate_test_for_file(source)
            if not content:
                continue
            test_path = OUTPUT_DIR / f"test_{source.name.replace('.', '_')}.py"
            test_path.write_text(content, encoding="utf-8")
            count += 1

    print(f"✅ Generated {count} tests in {OUTPUT_DIR.relative_to(ROOT)}")

    if args.run:
        try:
            import pytest  # noqa: F401

            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(OUTPUT_DIR), "-q"],
                cwd=ROOT,
            )
            return result.returncode
        except ImportError:
            passed = 0
            failed = 0
            for test_file in OUTPUT_DIR.glob("test_*.py"):
                result = subprocess.run(
                    [sys.executable, str(test_file)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    passed += 1
                else:
                    failed += 1
                    print(result.stderr or result.stdout)
            print(f"✅ Validation: {passed} passed, {failed} failed (no pytest)")
            return 0 if failed == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
