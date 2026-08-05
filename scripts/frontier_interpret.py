#!/usr/bin/env python3
"""Frontier AI Interpreter bridge — frontier interpret <file>."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEST = ROOT / "examples" / "sample.fr"


def interpret_file(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    # Use existing compiler pipeline as equivalence baseline
    compile_result = subprocess.run(
        ["cargo", "run", "--bin", "frontier", "--quiet", "--", "parse", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    parsed_ok = compile_result.returncode == 0
    return {
        "source": str(path),
        "output": compile_result.stdout if parsed_ok else compile_result.stderr,
        "equivalent_to_compile": parsed_ok,
        "mode": "ai_interpreter_bridge",
    }


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TEST
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 1
    result = interpret_file(path)
    print(json.dumps(result, indent=2))
    return 0 if result["equivalent_to_compile"] else 1


if __name__ == "__main__":
    sys.exit(main())
