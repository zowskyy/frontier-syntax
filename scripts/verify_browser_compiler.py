#!/usr/bin/env python3
"""Verify browser compiler + WASM codegen integration."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "frontier/core/knowledge.frontier",
    "frontier/core/wasm_codegen.frontier",
    "frontier/core/browser_compiler.frontier",
    "src/browser_compiler.rs",
    "src/wasm_codegen.rs",
    "src/knowledge_bridge.rs",
    "src/browser_wasm.rs",
    "browser/index.html",
    "browser/frontier_runtime.js",
    "browser/test_runner.js",
    "build.rs",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("FAIL: Missing browser compiler files:")
        for path in missing:
            print(f"  - {path}")
        return 1

    rc = subprocess.call(["cargo", "test", "--lib"], cwd=ROOT)
    if rc != 0:
        return rc

    example = ROOT / "examples" / "auto_optimize.fr"
    if not example.exists():
        example = ROOT / "examples" / "v2_parser_test.fr"
    rc = subprocess.call(
        [
            "cargo",
            "run",
            "--quiet",
            "--bin",
            "frontier",
            "--",
            "compile",
            str(example),
            "--target",
            "wasm",
            "--optimize",
            "-o",
            "/tmp/frontier_browser_test.wasm",
        ],
        cwd=ROOT,
    )

    if rc != 0:
        print("FAIL: frontier compile --target wasm")
        return rc

    print("PASS: Browser compiler verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
