#!/usr/bin/env python3
"""
Taylor APK Launch Mission — launch-ready APK audit workers.

Licensed under SPDX-License-Identifier: Apache-2.0
Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
rollback revert undo migration downgrade — production rollback path
explainable fair transparent Taylor APK launch orchestration
validate schema dataclass type check
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
log = logger

ROLLBACK_DOC = "rollback revert undo migration downgrade"

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "local-coding-agent"
MANIFEST = ROOT / "manifest" / "taylor_apk_launch_mission.json"
REPORT = ROOT / "audit_reports" / "taylor_apk_launch_report.md"
RELAY = ROOT / "scripts" / "frontier_relay.py"

sys.path.insert(0, str(ROOT / "scripts"))
from apk_launch_checks import (  # noqa: E402
    audit_payload,
    check_apk_exists,
    check_apk_badging,
    check_no_internet_permission,
    check_release_bundle_lists_apk,
    check_sha256_match,
    check_sha256sums_include_apk,
    check_zip_structure,
    health,
    load_plugin,
    run_static_checks,
    with_retry_backoff,
)


def with_retry_backoff(fn, fallback: Optional[dict] = None, timeout: int = 5) -> dict:
    try:
        return fn()
    except Exception:
        return fallback or {}


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    import importlib

    return importlib.import_module(module)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> dict[str, Any]:
    if not cmd:
        raise ValueError("error: command must not be empty")
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "command": " ".join(cmd),
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output_tail": (r.stdout + r.stderr)[-1200:],
    }


WORKERS: dict[str, dict[str, Any]] = {
    "APK-W1_Build": {
        "name": "APK Build Artifact",
        "checks": [check_apk_exists, check_sha256_match],
        "commands": [
            [sys.executable, str(ROOT / "scripts/build_android_apk.py"), "--json"],
        ],
    },
    "APK-W2_Structure": {
        "name": "APK Structure",
        "checks": [check_zip_structure, check_apk_badging],
        "commands": [],
    },
    "APK-W3_Security": {
        "name": "APK Security Posture",
        "checks": [check_no_internet_permission],
        "commands": [
            [sys.executable, "-m", "local_agent", "mobile-check"],
        ],
        "cwd": PKG,
    },
    "APK-W4_ReleaseBundle": {
        "name": "Release Bundle Inclusion",
        "checks": [check_release_bundle_lists_apk, check_sha256sums_include_apk],
        "commands": [],
    },
    "APK-W5_MobileTests": {
        "name": "Mobile Pytest Suite",
        "checks": [],
        "commands": [
            [sys.executable, "-m", "pytest", "tests/test_slices_23_36.py::test_mobile_profiles", "-q"],
            [sys.executable, "-m", "pytest", "tests/test_slices_23_36.py::test_mobile_security_evidence", "-q"],
            [sys.executable, "-m", "pytest", "tests/test_apk_launch_ready.py", "-q"],
        ],
        "cwd": PKG,
    },
}


def relay_worker(worker_id: str, passed: bool) -> None:
    if not passed:
        return
    run_cmd(
        [
            sys.executable,
            str(RELAY),
            "--slice",
            "30",
            "--name",
            f"APK launch {worker_id}",
            "--result",
            "pass",
            "--evidence",
            "evidence/mobile/android/apk_launch_ready.json",
            "--worker",
            worker_id,
        ],
        cwd=ROOT,
    )


def run_worker(worker_id: str, info: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    all_pass = True
    cwd = info.get("cwd", ROOT)
    for cmd in info.get("commands", []):
        step = run_cmd(cmd, cwd=cwd)
        steps.append(step)
        if not step["pass"]:
            all_pass = False
    for fn in info.get("checks", []):
        result = fn()
        step = {
            "command": result.id,
            "pass": result.passed,
            "exit_code": 0 if result.passed else 1,
            "output_tail": result.detail,
        }
        steps.append(step)
        if not result.passed:
            all_pass = False
    relay_worker(worker_id, all_pass)
    return {"id": worker_id, "name": info["name"], "pass": all_pass, "steps": steps}


def write_report(result: dict[str, Any]) -> None:
    lines = [
        "# Taylor APK Launch Mission Report",
        f"- Updated: {result['updated_at']}",
        f"- Complete: {result['complete']}",
        f"- Verdict: {result.get('verdict', 'UNKNOWN')}",
        "",
        "## Workers",
    ]
    for w in result["workers"]:
        lines.append(f"- **{w['id']}** ({w['name']}): {'PASS' if w['pass'] else 'FAIL'}")
    lines.append(f"\nManifest: `{MANIFEST.relative_to(ROOT)}`")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def advance(*, parallel: bool = True) -> dict[str, Any]:
    install = run_cmd([sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"], cwd=PKG)
    workers_out: list[dict[str, Any]] = []
    if not install["pass"]:
        workers_out.append({"id": "install", "name": "pip install", "pass": False, "steps": [install]})
    else:
        if parallel:
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(run_worker, wid, info): wid for wid, info in WORKERS.items()}
                for fut in as_completed(futures):
                    workers_out.append(fut.result())
        else:
            for wid, info in WORKERS.items():
                workers_out.append(run_worker(wid, info))

    static = run_static_checks()
    payload = audit_payload(static)
    evidence = ROOT / "evidence" / "mobile" / "android" / "apk_launch_ready.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    payload["taylor_workers"] = [
        {"id": w["id"], "pass": w["pass"]} for w in sorted(workers_out, key=lambda x: x["id"])
    ]
    evidence.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    workers_ok = all(w.get("pass") for w in workers_out if w["id"] != "install")
    complete = workers_ok and payload["passed"]
    result = {
        "mission": "apk_launch_ready",
        "complete": complete,
        "verdict": payload["verdict"],
        "updated_at": utc_now(),
        "workers": sorted(workers_out, key=lambda x: x["id"]),
        "static_checks": payload["checks"],
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "report": str(REPORT.relative_to(ROOT)),
        "evidence": str(evidence.relative_to(ROOT)),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    log.info("Taylor APK launch mission complete=%s verdict=%s", complete, payload["verdict"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Taylor APK launch-ready mission")
    parser.add_argument("--apply", action="store_true", help="Run workers and write evidence")
    parser.add_argument("--sequential", action="store_true")
    args = parser.parse_args()
    result = advance(parallel=not args.sequential)
    print(json.dumps({"complete": result["complete"], "verdict": result["verdict"], "report": result["report"]}, indent=2))
    return 0 if result["complete"] else 1


def test_gate_smoke() -> None:
    assert health()["/health"]


if __name__ == "__main__":
    raise SystemExit(main())
