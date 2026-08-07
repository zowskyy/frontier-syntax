#!/usr/bin/env python3
"""Validate a single Frontier training sample (compile + wasmtime)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def compile_fr(source: str, out: Path) -> tuple[bool, str]:
    src = out.with_suffix(".fr")
    src.write_text(source, encoding="utf-8")
    r = subprocess.run(
        [
            "cargo", "run", "--quiet", "--bin", "frontier", "--",
            "compile", str(src), "-t", "wasm", "-o", str(out), "--no-optimize",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and out.exists(), (r.stdout + r.stderr)[-400:]


def run_wasm(wasm: Path, expected: int) -> tuple[bool, str]:
    wasmtime = shutil.which("wasmtime")
    if not wasmtime:
        return False, "wasmtime not found"
    data = wasm.read_bytes()
    escaped = "".join(f"\\{b:02x}" for b in data)
    wast = wasm.with_suffix(".wast")
    wast.write_text(
        f'(module binary "{escaped}")\n(assert_return (invoke "main") (i32.const {expected}))\n',
        encoding="utf-8",
    )
    r = subprocess.run([wasmtime, "wast", str(wast)], cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-200:]


def validate_sample(completion: str, expected: int | None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wasm = Path(tmp) / "sample.wasm"
        ok_compile, compile_out = compile_fr(completion, wasm)
        ok_run, run_out = (False, "skipped")
        if ok_compile and expected is not None:
            ok_run, run_out = run_wasm(wasm, expected)
        elif ok_compile:
            ok_run = True
        return {
            "compile_pass": ok_compile,
            "wasmtime_pass": ok_run,
            "pass": ok_compile and ok_run,
            "compile_output": compile_out,
            "wasmtime_output": run_out,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one training sample")
    parser.add_argument("--json", type=str, help="Sample JSON object")
    parser.add_argument("--file", type=Path, help="Path to .fr source")
    parser.add_argument("--expected", type=int, help="Expected main return")
    args = parser.parse_args()

    if args.json:
        sample = json.loads(args.json)
        result = validate_sample(sample["completion"], sample.get("expected_return"))
    elif args.file:
        source = args.file.read_text(encoding="utf-8")
        result = validate_sample(source, args.expected)
    else:
        parser.error("provide --json or --file")
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
