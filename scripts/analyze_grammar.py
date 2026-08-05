#!/usr/bin/env python3
"""Cycle 3: Static grammar analyzer for orthogonality and reachability."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = ROOT / "syntax" / "Frontier.g4"
TOKEN_TABLE = ROOT / "syntax" / "token_regex_table.json"
FEATURE_MATRIX = ROOT / "syntax" / "feature_matrix.json"

DEAD_TERMINALS = ["LBRACKET", "RBRACKET"]


def strip_comments(text: str) -> str:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return text


def analyze():
    grammar = strip_comments(GRAMMAR.read_text())
    tokens = json.loads(TOKEN_TABLE.read_text())
    matrix = json.loads(FEATURE_MATRIX.read_text())

    issues = []

    if "++" in grammar:
        issues.append("Increment operator (++) present in grammar")
    if re.search(r"(?<![-+])--(?![->])", grammar):
        issues.append("Decrement operator (--) present in grammar")

    grammar_tokens = set(re.findall(r"\b([A-Z][A-Z_0-9]+)\b", grammar))
    lexer_tokens = {k for k, v in tokens["tokens"].items() if v.get("emits_token") is not False}

    for dead in DEAD_TERMINALS:
        if dead in lexer_tokens:
            issues.append(f"Dead terminal {dead} still in token table")
        if dead in grammar_tokens:
            issues.append(f"Dead terminal {dead} still in grammar")

    if re.search(r"methodCall|obj\.method", grammar, re.I):
        issues.append("Method-call syntax present")

    op_count = len(matrix["operations"])
    unique = all(v.get("unique") for v in matrix["operations"].values())

    print(f"Grammar file: {GRAMMAR}")
    print(f"Operations mapped: {op_count}")
    print(f"All operations unique: {unique}")
    print(f"Removed features: {list(matrix['removed_features'].keys())}")
    print(f"Dead terminals removed: {DEAD_TERMINALS}")

    if issues:
        print("FAIL:")
        for i in issues:
            print(f"  - {i}")
        return 1

    print("PASS: Cycle 3 grammar analysis")
    return 0


if __name__ == "__main__":
    sys.exit(analyze())
