#!/usr/bin/env python3
"""Phase 5 M5 gate — compile frontier/src/main.fr via native wasmtime path."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "frontier" / "src" / "main.fr"
MANIFEST = ROOT / "manifest" / "main_fr_native.json"
MISSION = ROOT / "manifest" / "compiler_self_host_mission.json"

# compile(8): lex=9, parse=10, codegen=420, hash=420 → 840
EXPECTED_MAIN = 840


def run_native(source: Path, expected: int, out_name: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_native_self_host.py"),
        "--source",
        str(source),
        "--expected",
        str(expected),
        "--output-name",
        out_name,
    ]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"pass": False, "error": (r.stdout + r.stderr)[-500:]}
    data["exit_code"] = r.returncode
    return data


def update_m5(passing: bool) -> None:
    if not MISSION.exists():
        return
    data = json.loads(MISSION.read_text(encoding="utf-8"))
    m5 = data.setdefault("milestones", {}).setdefault("M5", {})
    m5["pass"] = passing
    m5["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if passing:
        m5["reason"] = "main.fr native wasmtime self-host verified"
    else:
        m5.setdefault("reason", "main.fr native path not passing")
    data["updated_at"] = m5["updated_at"]
    MISSION.write_text(json.dumps(data, indent=2), encoding="utf-8")


def verify() -> dict:
    if not MAIN.exists():
        result = {"pass": False, "error": f"missing {MAIN}"}
    else:
        native = run_native(MAIN, EXPECTED_MAIN, "native_main_fr.wasm")
        result = {
            "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "script": "scripts/verify_main_fr_native.py",
            "source": str(MAIN.relative_to(ROOT)),
            "expected_main": EXPECTED_MAIN,
            "native": native,
            "pass": native.get("pass") is True,
            "milestone": "M5",
        }

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_m5(result.get("pass", False))
    return result


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2))
    if result.get("pass"):
        print("PASS: main.fr native self-host (M5)")
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
