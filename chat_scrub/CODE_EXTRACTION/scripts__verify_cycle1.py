#!/usr/bin/env python3
"""Cycle 1 verification: validate token_regex_table.json against hard-gate criteria."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE_PATH = ROOT / "syntax" / "token_regex_table.json"
LEXICON_PATH = ROOT / "syntax" / "lexicon.ebnf"

KEYWORDS = [
    "let", "fn", "return", "if", "else",
    "true", "false", "null",
    "int", "float", "bool", "string", "void",
]

def check_prefix_disjointness():
  """Verify no keyword is a prefix of another keyword."""
  for i, a in enumerate(KEYWORDS):
    for b in KEYWORDS[i + 1:]:
      if a.startswith(b) or b.startswith(a):
        raise AssertionError(f"Keyword prefix conflict: {a!r} / {b!r}")
  if "iff" in KEYWORDS:
    raise AssertionError("Banned keyword 'iff' must not appear")

def check_identifier_pattern():
  pat = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
  for kw in KEYWORDS:
    assert not pat.fullmatch(kw) or kw in KEYWORDS
  assert pat.fullmatch("iff")
  assert pat.fullmatch("ifoo")
  assert not pat.fullmatch("9bad")

def check_regex_compile(table):
  errors = []
  for name, spec in table["tokens"].items():
    if spec.get("emits_token") is False:
      continue
    try:
      re.compile(spec["pattern"])
    except re.error as e:
      errors.append(f"{name}: {e}")
  if errors:
    raise AssertionError("Invalid regex patterns:\n" + "\n".join(errors))

def check_artifacts_exist():
  assert TABLE_PATH.exists(), f"Missing {TABLE_PATH}"
  assert LEXICON_PATH.exists(), f"Missing {LEXICON_PATH}"
  content = LEXICON_PATH.read_text()
  assert "re2c" in content
  assert "NFC" in content
  assert "iff" in content and "banned" in content

def main():
  check_artifacts_exist()
  table = json.loads(TABLE_PATH.read_text())
  assert table["engine"] == "re2c"
  assert table["encoding"] == "UTF-8"
  assert table["normalization"] == "NFC"
  assert table["time_complexity"] == "O(n)"
  check_prefix_disjointness()
  check_identifier_pattern()
  check_regex_compile(table)
  token_count = sum(
    1 for t in table["tokens"].values() if t.get("emits_token") is not False
  )
  print(f"PASS: Cycle 1 verification ({token_count} emitting tokens)")
  return 0

if __name__ == "__main__":
  sys.exit(main())
