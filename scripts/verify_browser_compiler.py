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

    wasm32 = subprocess.call(
        ["cargo", "build", "--release", "--lib", "--target", "wasm32-unknown-unknown"],
        cwd=ROOT,
    )
    if wasm32 != 0:
        print("FAIL: wasm32 build")
        return wasm32

    wasm_bin = ROOT / "target" / "wasm32-unknown-unknown" / "release" / "frontier.wasm"
    bindings_dir = ROOT / "browser" / "wasm-bindings"
    bindings_dir.mkdir(parents=True, exist_ok=True)
    rc = subprocess.call(
        [
            "wasm-bindgen",
            str(wasm_bin),
            "--out-dir",
            str(bindings_dir),
            "--target",
            "web",
            "--out-name",
            "frontier_browser",
        ],
        cwd=ROOT,
    )
    if rc != 0:
        print("FAIL: wasm-bindgen (install wasm-bindgen-cli if missing)")
        return rc

    syntax_wasm = ROOT / "syntax" / "wasm"
    syntax_wasm.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy2(wasm_bin, syntax_wasm / "frontier_browser.wasm")

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
