#!/usr/bin/env python3
"""
Phase 1 slice 1.1 — empirical WASM execution via wasmtime wast.

Compiles Frontier source, embeds WASM in a .wast script, and asserts the
return value of exported `main` with wasmtime (not just compile-time checks).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "wasm_codegen_verify.json"

CASES = [
    {
        "name": "const_return",
        "source": "fn main(): int { return 42; }",
        "expected": 42,
    },
    {
        "name": "let_if",
        "source": """fn main(): int {
    let x: int = 10;
    if (x > 5) {
        return x;
    }
    return 0;
}""",
        "expected": 10,
    },
    {
        "name": "while_loop",
        "source": """fn main(): int {
    let flag: int = 1;
    while (flag > 0) {
        return 13;
    }
    return 0;
}""",
        "expected": 13,
    },
    {
        "name": "function_call",
        "source": """fn double(x: int): int {
    return x * 2;
}
fn main(): int {
    return double(21);
}""",
        "expected": 42,
    },
]


def find_wasmtime() -> str | None:
    return shutil.which("wasmtime")


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


def make_wast(wasm: Path, expected: int) -> str:
    data = wasm.read_bytes()
    escaped = "".join(f"\\{b:02x}" for b in data)
    return (
        f'(module binary "{escaped}")\n'
        f'(assert_return (invoke "main") (i32.const {expected}))\n'
    )


def run_wasm(wasm: Path, expected: int) -> tuple[bool, int | None, str]:
    wasmtime = find_wasmtime()
    if not wasmtime:
        return False, None, "wasmtime not found"

    wast = wasm.with_suffix(".wast")
    wast.write_text(make_wast(wasm, expected), encoding="utf-8")
    r = subprocess.run(
        [wasmtime, "wast", str(wast)],
        capture_output=True,
        text=True,
    )
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        return False, None, out
    return True, expected, out or "ok"


def verify() -> dict:
    wasmtime = find_wasmtime()
    results = []
    all_ok = True

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for case in CASES:
            wasm = tmp_path / f"{case['name']}.wasm"
            ok_compile, compile_out = compile_fr(case["source"], wasm)
            ok_run, val, run_out = (False, None, "compile failed")
            if ok_compile:
                ok_run, val, run_out = run_wasm(wasm, case["expected"])
            ok = ok_compile and ok_run and val == case["expected"]
            if not ok:
                all_ok = False
            results.append({
                "name": case["name"],
                "pass": ok,
                "expected": case["expected"],
                "actual": val,
                "compile_ok": ok_compile,
                "run_ok": ok_run,
                "output": run_out[-200:] if run_out else compile_out[-200:],
            })

    summary = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_wasm_codegen.py",
        "wasmtime": wasmtime,
        "all_pass": all_ok,
        "cases": results,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"pass": all_ok, **summary}


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
