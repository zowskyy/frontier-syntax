#!/usr/bin/env python3
"""Map frontier/core/*.frontier specs to Rust implementations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "frontier" / "core"

SPEC_TO_RUST = {
    "parser.frontier": "src/parser/mod.rs",
    "types.frontier": "src/resolver.rs",
    "memory.frontier": "src/resolver.rs",
    "concurrency.frontier": "src/unity.rs",
    "errors.frontier": "src/error.rs",
    "stdlib.frontier": "src/lib.rs",
    "compiler.frontier": "src/compiler/mod.rs",
    "knowledge.frontier": "src/knowledge_bridge.rs",
    "wasm_codegen.frontier": "src/wasm_codegen.rs",
    "browser_compiler.frontier": "src/browser_compiler.rs",
}


def verify() -> dict:
    specs = sorted(CORE.glob("*.frontier"))
    mappings = []
    all_ok = True
    for spec in specs:
        rust_rel = SPEC_TO_RUST.get(spec.name)
        rust_path = ROOT / rust_rel if rust_rel else None
        ok = rust_path is not None and rust_path.exists()
        mappings.append({"spec": spec.name, "rust": rust_rel, "present": ok})
        all_ok = all_ok and ok
    return {"pass": all_ok, "mappings": mappings, "count": len(specs)}


def main() -> int:
    result = verify()
    manifest = ROOT / "manifest" / "spec_impl_bridge.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if result["pass"]:
        print(f"PASS: Spec/impl bridge — {result['count']} core modules mapped")
        return 0
    missing = [m for m in result["mappings"] if not m["present"]]
    print(f"FAIL: unmapped specs: {missing}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
