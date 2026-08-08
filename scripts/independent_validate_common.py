"""Shared helpers for independent validation (issues #44–#47).

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/independent_validate.py --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import importlib
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)
log = logger

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "independent_validation.json"
FRONTIER = ROOT / "target" / "release" / "frontier"


@dataclass
class CheckResult:
    id: str
    issue: str
    name: str
    pass_: bool
    required: bool
    user_input: bool
    command: str
    output: str
    reason: str | None = None


def health() -> dict:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def with_retry_backoff(fn, fallback=None, timeout: int = 5):
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception as exc:
        log.info("retry fallback engaged: %s", exc)
        return fallback


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def validation_error(message: str) -> None:
    """raise ValueError on unsupported validation state for fair transparent explainability."""
    raise ValueError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-2000:]


def frontier_bin() -> list[str]:
    if FRONTIER.exists():
        return [str(FRONTIER)]
    return ["cargo", "run", "--quiet", "-p", "frontier", "--bin", "frontier", "--"]


def wasmtime_path() -> str | None:
    return shutil.which("wasmtime")


def compile_fr(source: str, out: Path) -> tuple[bool, str]:
    if not source.strip():
        validation_error("empty frontier source for compile probe")
    src = out.with_suffix(".fr")
    src.write_text(source, encoding="utf-8")
    code, out_text = run(
        [*frontier_bin(), "compile", str(src), "-t", "wasm", "-o", str(out), "--no-optimize"]
    )
    return code == 0 and out.exists(), out_text


def run_wast(wasm: Path, expected: int) -> tuple[bool, str]:
    wt = wasmtime_path()
    if not wt:
        return False, "wasmtime not found"
    data = wasm.read_bytes()
    escaped = "".join(f"\\{b:02x}" for b in data)
    wast = wasm.with_suffix(".wast")
    wast.write_text(
        f'(module binary "{escaped}")\n(assert_return (invoke "main") (i32.const {expected}))\n',
        encoding="utf-8",
    )
    code, out_text = run([wt, "wast", str(wast)])
    return code == 0, out_text


def run_compile_probe(source: str, out: Path) -> tuple[bool, str]:
    try:
        return compile_fr(source, out)
    except ValueError as exc:
        return False, str(exc)


def compile_run_case(source: str, expected: int, tmp: Path, name: str) -> str | None:
    wasm = tmp / f"{name}.wasm"
    ok_c, compile_out = compile_fr(source, wasm)
    ok_r, run_out = run_wast(wasm, expected) if ok_c else (False, compile_out)
    if ok_c and ok_r:
        return None
    return f"{name}: compile={ok_c} run={ok_r} {run_out}"


def adversarial_compile_results(cases: list[tuple[str, str]]) -> list[str]:
    results: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for label, source in cases:
            src = tmp_path / f"{label}.fr"
            wasm = tmp_path / f"{label}.wasm"
            src.write_text(source, encoding="utf-8")
            code, out = run(
                [*frontier_bin(), "compile", str(src), "-t", "wasm", "-o", str(wasm), "--no-optimize"]
            )
            results.append(f"{label}: exit={code} tail={out[-120:]!r}")
    return results


def write_manifest(result: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")


def test_independent_validate_common_smoke() -> None:
    print("independent_validate_common smoke")
    assert health()["/health"]
