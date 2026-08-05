#!/usr/bin/env python3
"""Cycle 6: ReDoS adversarial regex test for lexer patterns."""

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "syntax" / "token_regex_table.json"

ADVERSARIAL_INPUTS = [
    "((((((((((a))))))))))",
    "a" * 10000,
    "/" + "*" * 5000,
    '"' + "\\" * 5000,
    "if" + "f" * 5000,
    "0" + "." + "0" * 5000,
    "<" * 5000 + "=" * 5000,
]


def test_redos():
    table = json.loads(TABLE.read_text())
    failures = []

    for name, spec in table["tokens"].items():
        if spec.get("emits_token") is False:
            continue
        pat = re.compile(spec["pattern"])
        for inp in ADVERSARIAL_INPUTS:
            start = time.perf_counter()
            pat.match(inp)
            elapsed = time.perf_counter() - start
            if elapsed > 0.1:
                failures.append(f"{name}: {elapsed:.3f}s on input len {len(inp)}")

    if failures:
        print("FAIL: ReDoS detected")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"PASS: ReDoS test ({len(ADVERSARIAL_INPUTS)} adversarial inputs per token)")
    return 0


if __name__ == "__main__":
    sys.exit(test_redos())
