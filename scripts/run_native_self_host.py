#!/usr/bin/env python3
"""Native self-host path — wasmtime + Frontier compiler WASM (no bootstrap.run / cargo)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "native_self_host.json"
COMPILER_WASM = ROOT / "target" / "wasm32-unknown-unknown" / "release" / "frontier.wasm"
HOST_BIN = ROOT / "target" / "release" / "frontier_wasm_host"
SOURCE = ROOT / "frontier" / "src" / "self_host_probe.fr"
WASM_MAGIC = b"\0asm"

BUILD_COMPILER = [
    "cargo", "build", "--release", "--lib",
    "--target", "wasm32-unknown-unknown",
    "--no-default-features", "--features", "wasm-slim,wasm-host-only",
]
BUILD_HOST = ["cargo", "build", "--release", "--bin", "frontier_wasm_host"]


def run(cmd: list[str]) -> tuple[bool, str]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-800:]


def valid_wasm(path: Path) -> bool:
    if not path.exists():
        return False
    data = path.read_bytes()
    return len(data) >= 8 and data[:4] == WASM_MAGIC


def run_wasm_main(wasm: Path, expected: int = 42) -> tuple[bool, str]:
    data = wasm.read_bytes()
    escaped = "".join(f"\\{b:02x}" for b in data)
    wast = wasm.with_suffix(".wast")
    wast.write_text(
        f'(module binary "{escaped}")\n'
        f'(assert_return (invoke "main") (i32.const {expected}))\n',
        encoding="utf-8",
    )
    r = subprocess.run(["wasmtime", "wast", str(wast)], cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-300:]


def ensure_artifacts() -> tuple[bool, str]:
    ok, out = run(BUILD_COMPILER)
    if not ok:
        return False, f"compiler wasm build failed: {out}"
    if not COMPILER_WASM.exists():
        return False, f"missing {COMPILER_WASM}"
    ok, out = run(BUILD_HOST)
    if not ok:
        return False, f"host build failed: {out}"
    if not HOST_BIN.exists():
        return False, f"missing {HOST_BIN}"
    return True, "ok"


def native_self_host() -> dict:
    if not SOURCE.exists():
        return {"pass": False, "error": f"missing {SOURCE}"}

    ok, msg = ensure_artifacts()
    if not ok:
        return {"pass": False, "error": msg}

    out_path = ROOT / "target" / "native_self_host_probe.wasm"
    ok, out = run([
        str(HOST_BIN), str(COMPILER_WASM), str(SOURCE), "-o", str(out_path),
    ])
    if not ok or not out_path.exists():
        return {"pass": False, "stage": "native_wasmtime", "error": out}

    wasm_ok = valid_wasm(out_path)
    run_ok, run_out = run_wasm_main(out_path) if wasm_ok else (False, "invalid wasm")

    result = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/run_native_self_host.py",
        "source": str(SOURCE.relative_to(ROOT)),
        "compiler_wasm": str(COMPILER_WASM.relative_to(ROOT)),
        "host": str(HOST_BIN.relative_to(ROOT)),
        "output_wasm": str(out_path.relative_to(ROOT)),
        "output_bytes": out_path.stat().st_size,
        "valid_wasm": wasm_ok,
        "main_returns_42": run_ok,
        "pass": wasm_ok and run_ok,
        "bootstrap_cargo_on_recompile": False,
        "mode": "native_wasmtime",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = native_self_host()
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
