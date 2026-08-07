#!/usr/bin/env python3
"""Verify frontier-dex gates: tests, benchmark, tracking, and artifacts."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEX_DIR = ROOT / "frontier-dex"
TRACKING_PATH = DEX_DIR / "TRACKING.json"
BENCHMARK_SCRIPT = DEX_DIR / "benchmark.sh"
EXPECTED_SLICES = [f"S-{i:02d}" for i in range(1, 11)]

TEST_RESULT_RE = re.compile(
    r"test result: (?:ok|FAILED)\.\s+(\d+) passed;\s+(\d+) failed"
)


def run_cargo_tests() -> dict:
    result = subprocess.run(
        ["cargo", "test", "-p", "frontier-dex"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    passed = failed = 0
    for match in TEST_RESULT_RE.finditer(output):
        passed += int(match.group(1))
        failed += int(match.group(2))
    return {
        "ok": result.returncode == 0 and failed == 0,
        "exit_code": result.returncode,
        "passed": passed,
        "failed": failed,
    }


def run_benchmark() -> dict:
    result = subprocess.run(
        ["bash", str(BENCHMARK_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    gate_match = re.search(r"BENCHMARK_GATE=(\w+)", output)
    gate = gate_match.group(1) if gate_match else None
    return {
        "ok": result.returncode == 0 and gate == "PASS",
        "exit_code": result.returncode,
        "gate": gate,
    }


def check_tracking() -> dict:
    if not TRACKING_PATH.exists():
        return {
            "ok": False,
            "error": f"missing {TRACKING_PATH.relative_to(ROOT)}",
            "slices_total": 0,
            "slices_passed": 0,
            "failed_slices": [],
        }

    data = json.loads(TRACKING_PATH.read_text())
    slices = data.get("slices", {})
    failed_slices = []
    for slice_id in EXPECTED_SLICES:
        slice_info = slices.get(slice_id)
        if slice_info is None:
            failed_slices.append({"id": slice_id, "reason": "missing"})
        elif slice_info.get("status") != "passed":
            failed_slices.append(
                {"id": slice_id, "reason": f"status={slice_info.get('status')!r}"}
            )

    return {
        "ok": len(failed_slices) == 0,
        "slices_total": len(EXPECTED_SLICES),
        "slices_passed": len(EXPECTED_SLICES) - len(failed_slices),
        "failed_slices": failed_slices,
    }


def check_artifacts() -> dict:
    proofs = sorted(p.name for p in (DEX_DIR / "proofs").glob("*.v"))
    zk_files = sorted(p.name for p in (DEX_DIR / "zk").glob("*.zk"))
    ok = bool(proofs) and bool(zk_files)
    return {
        "ok": ok,
        "proofs": proofs,
        "zk": zk_files,
    }


def main() -> int:
    summary = {
        "module": "frontier-dex",
        "cargo_test": run_cargo_tests(),
        "benchmark": run_benchmark(),
        "tracking": check_tracking(),
        "artifacts": check_artifacts(),
    }
    summary["ok"] = all(
        summary[key]["ok"] for key in ("cargo_test", "benchmark", "tracking", "artifacts")
    )

    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
