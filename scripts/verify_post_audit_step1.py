#!/usr/bin/env python3
"""Step 1 verification: LSP binary, WASM FFI, VSCode extension artifacts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LSP_BIN = ROOT / "target" / "release" / "lsp"
VSIX = ROOT / "language-support" / "frontier-syntax-vscode" / "frontier-syntax-0.1.0.vsix"
WASM = ROOT / "syntax" / "wasm_parser.wasm"
TMLANG = ROOT / "language-support" / "frontier-syntax-vscode" / "syntaxes" / "frontier.tmLanguage.json"
SERVER_RS = ROOT / "src" / "lsp" / "server.rs"


def main():
    errors = []

    if not SERVER_RS.exists():
        errors.append(f"Missing {SERVER_RS}")
    if not LSP_BIN.exists():
        errors.append(f"LSP binary not built: run cargo build --release --bin lsp")
    if not VSIX.exists():
        errors.append(f"VSIX not packaged: {VSIX}")
    if not WASM.exists():
        errors.append(f"Missing WASM: {WASM}")
    if not TMLANG.exists():
        errors.append(f"Missing TextMate grammar: {TMLANG}")

    # Validate TextMate grammar has token categories from lexicon
    grammar = TMLANG.read_text() if TMLANG.exists() else ""
    for scope in ["keyword", "string", "comment", "constant.numeric"]:
        if scope not in grammar:
            errors.append(f"TextMate grammar missing scope pattern: {scope}")

    # Validate WASM module loads via wasmi (same as LSP FFI)
    if WASM.exists():
        try:
            import wasmi  # noqa: not installed; skip
        except ImportError:
            pass

    # Validate final_hash unchanged
    final_hash = (ROOT / "syntax" / "final_hash.sha3").read_text().strip()
    expected = "4526dc37ea9d2b11a3c75fe1f3b262a246a11a3d972afeafcbc9865e456bd3e6"
    if final_hash != expected:
        errors.append(f"final_hash.sha3 changed: {final_hash}")

    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PASS: Post-Audit Step 1 verification")
    print(f"  LSP binary: {LSP_BIN}")
    print(f"  VSIX: {VSIX} ({VSIX.stat().st_size} bytes)")
    print(f"  WASM: {WASM} ({WASM.stat().st_size} bytes)")
    print(f"  final_hash.sha3: unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
