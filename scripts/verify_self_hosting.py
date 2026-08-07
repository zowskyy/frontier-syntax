#!/usr/bin/env python3
"""Verify Frontier self-hosting — bootstrap and native (wasmtime) paths."""

from __future__ import annotations

import argparse
import filecmp
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "frontier" / "src" / "main.fr"
MANIFEST = ROOT / "manifest" / "self_hosting_verify.json"


def run(cmd: list[str], cwd: Path = ROOT) -> tuple[bool, str]:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0, out


def verify_bootstrap() -> dict:
    if not MAIN.exists():
        return {"pass": False, "error": f"missing {MAIN}"}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bootstrap = tmp_path / "bootstrap"
        self_hosted = tmp_path / "self_hosted"
        launcher = tmp_path / "bootstrap.run"

        ok, out = run(
            [
                "cargo",
                "run",
                "--quiet",
                "--bin",
                "frontier",
                "--",
                "compile",
                str(MAIN),
                "--bootstrap",
                "-o",
                str(bootstrap),
            ]
        )
        if not ok:
            return {"pass": False, "error": f"genesis compile\n{out}"}

        if not bootstrap.exists() or not launcher.exists():
            return {"pass": False, "error": "bootstrap artifacts missing"}

        ok, out = run([str(launcher), "compile", str(MAIN), "-o", str(self_hosted)])
        if not ok or not self_hosted.exists():
            return {"pass": False, "error": f"bootstrap recompile\n{out}"}

        identical = filecmp.cmp(bootstrap, self_hosted, shallow=False)
        return {
            "pass": identical,
            "mode": "bootstrap",
            "uses_cargo_on_recompile": True,
            "output": "PASS: Self-hosting bootstrap (cmp identical)" if identical else "FAIL: differ",
        }


def verify_native() -> dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_native_self_host.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"pass": False, "error": (r.stdout + r.stderr)[-400:]}
    data["mode"] = "native"
    data["uses_cargo_on_recompile"] = False
    if data.get("pass"):
        data["output"] = "PASS: Native self-host (wasmtime + Frontier compiler WASM)"
    return data


def verify(*, native: bool = False, full: bool = False) -> dict:
    bootstrap = verify_bootstrap()
    native_result = verify_native()

    result = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_self_hosting.py",
        "source": str(MAIN.relative_to(ROOT)),
        "bootstrap_pass": bootstrap.get("pass", False),
        "native_pass": native_result.get("pass", False),
        "bootstrap": bootstrap,
        "native": native_result,
    }

    if full:
        result["pass"] = result["bootstrap_pass"] and result["native_pass"]
    elif native:
        result["pass"] = result["native_pass"]
    else:
        result["pass"] = result["bootstrap_pass"]

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Verify Frontier self-hosting")
    p.add_argument("--native", action="store_true", help="require native wasmtime path (closes #46)")
    p.add_argument("--full", action="store_true", help="require bootstrap + native")
    args = p.parse_args()

    result = verify(native=args.native, full=args.full)
    print(json.dumps(result, indent=2))
    if result.get("native_pass"):
        print("PASS: Native self-host (wasmtime + Frontier compiler WASM)")
    elif result.get("bootstrap_pass") and not args.native:
        print(result["bootstrap"].get("output", "PASS: bootstrap"))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
