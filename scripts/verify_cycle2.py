#!/usr/bin/env python3
"""Cycle 2 verification: grammar artifacts + extension tokens + example programs."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT_PATH = ROOT / "syntax" / "cycle2" / "extensions.json"
GRAMMAR_PATH = ROOT / "syntax" / "grammar.g4"
AST_PATH = ROOT / "syntax" / "ast_sample.json"
EXAMPLES = ROOT / "examples" / "community"

CYCLE2_KEYWORDS = [
    "module", "import", "type", "extern", "opaque", "for", "in", "as", "Ok", "Err",
]


def main():
    assert EXT_PATH.exists(), f"Missing {EXT_PATH}"
    assert GRAMMAR_PATH.exists(), f"Missing {GRAMMAR_PATH}"
    assert AST_PATH.exists(), f"Missing {AST_PATH}"

    ext = json.loads(EXT_PATH.read_text())
    assert ext["cycle"] == 2
    for kw in CYCLE2_KEYWORDS:
        token_name = f"KW_{kw.upper()}" if kw not in ("Ok", "Err") else f"KW_{kw.upper()}"
        if kw in ("Ok", "Err"):
            token_name = f"KW_{kw.upper()}"
        assert any(
            spec.get("literal") == kw for spec in ext["tokens"].values()
        ), f"Missing keyword {kw}"

    for name, spec in ext["tokens"].items():
        re.compile(spec["pattern"])

    example_count = sum(1 for d in EXAMPLES.iterdir() if (d / "app.frontier").exists())
    assert example_count >= 5, f"Expected >=5 community examples, got {example_count}"

    grammar = GRAMMAR_PATH.read_text()
    assert "moduleDecl" in grammar
    assert "importDecl" in grammar

    ast = json.loads(AST_PATH.read_text())
    assert ast["program"]["kind"] == "Program"

    print(f"PASS: Cycle 2 verification ({len(ext['tokens'])} extension tokens, {example_count} examples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
