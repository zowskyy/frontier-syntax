#!/usr/bin/env python3
"""Phase 7 production hardening gate."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "phase7_hardening_verify.json"


def run(cmd: list[str], timeout: int = 900) -> dict:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {"pass": r.returncode == 0, "exit_code": r.returncode, "command": " ".join(cmd), "output": (r.stdout + r.stderr)[-800:]}
    except FileNotFoundError as e:
        return {"pass": False, "exit_code": -1, "command": " ".join(cmd), "output": str(e)}
    except subprocess.TimeoutExpired:
        return {"pass": False, "exit_code": -1, "command": " ".join(cmd), "output": "timeout"}


def gate_stability() -> dict:
    runs = []
    for _ in range(2):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tracking.py"), "gate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            data = {"all_pass": False, "parse_error": True}
        runs.append({"exit_code": r.returncode, "summary": data})

    if len(runs) < 2:
        return {"pass": False, "reason": "insufficient runs"}

    a, b = runs[0]["summary"], runs[1]["summary"]
    keys = ("phase_0_pass", "phase_1_pass", "phase_2_pass", "phase_3_pass", "phase_4_pass", "phase_5_pass", "phase_6_pass", "phase_7_pass", "all_pass")
    stable = all(a.get(k) == b.get(k) for k in keys if k in a or k in b)
    return {"pass": stable and runs[0]["exit_code"] == runs[1]["exit_code"], "runs": runs}


def verify() -> dict:
    clippy = run(["cargo", "clippy", "--lib", "--", "-D", "warnings"])
    agent = run([sys.executable, str(ROOT / "scripts" / "verify_agent_security.py")])
    compiler_ci = {"pass": (ROOT / ".github" / "workflows" / "compiler-gate.yml").exists()}
    stability = gate_stability()

    ok = clippy["pass"] and agent["pass"] and compiler_ci["pass"] and stability["pass"]
    result = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_phase7_hardening.py",
        "clippy": clippy,
        "agent_security": agent,
        "compiler_ci": compiler_ci,
        "gate_stability": stability,
        "pass": ok,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2))
    if result["pass"]:
        print("PASS: Phase 7 production hardening")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
