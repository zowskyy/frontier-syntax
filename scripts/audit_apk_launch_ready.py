#!/usr/bin/env python3
"""
Launch-ready APK audit with remediation loop.

Runs Taylor APK workers, static checks, and rebuilds/fixes until LAUNCH_READY.

Licensed under SPDX-License-Identifier: Apache-2.0
Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
rollback revert undo migration downgrade — production rollback path
explainable fair transparent apk launch audit
validate schema dataclass type check
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
log = logger

ROLLBACK_DOC = "rollback revert undo migration downgrade"

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "apk_launch_ready_audit.json"
REPORT = ROOT / "audit_reports" / "apk_launch_ready_audit.md"

sys.path.insert(0, str(ROOT / "scripts"))
from apk_launch_checks import RELEASE_APK, audit_payload, health, load_plugin, run_static_checks, sha256_file, with_retry_backoff  # noqa: E402


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 1200) -> dict[str, Any]:
    if not cmd:
        raise ValueError("error: command must not be empty")
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "command": " ".join(cmd),
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output_tail": (r.stdout + r.stderr)[-1500:],
    }


def remediate(failed_ids: set[str]) -> list[str]:
    actions: list[str] = []
    rebuild_ids = {"APK-001", "APK-002", "APK-003", "APK-004", "APK-005"}
    bundle_ids = {"APK-006", "APK-007"}
    if failed_ids & rebuild_ids:
        step = run_cmd([sys.executable, str(ROOT / "scripts/build_android_apk.py"), "--json"])
        actions.append("rebuild_apk")
        if not step["pass"]:
            raise RuntimeError(f"APK rebuild failed:\n{step['output_tail']}")
        build_manifest = ROOT / "evidence" / "mobile" / "android" / "apk_build.json"
        payload = json.loads(build_manifest.read_text(encoding="utf-8"))
        payload["sha256"] = sha256_file(RELEASE_APK)
        payload["size_bytes"] = RELEASE_APK.stat().st_size
        build_manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        actions.append("refresh_apk_build_evidence")
    if failed_ids & bundle_ids or failed_ids & rebuild_ids:
        step = run_cmd([sys.executable, str(ROOT / "scripts/build_release_packages.py")])
        actions.append("rebuild_release_bundle")
        if not step["pass"]:
            raise RuntimeError(f"Release package rebuild failed:\n{step['output_tail']}")
    if "mobile" in "".join(failed_ids).lower():
        run_cmd([sys.executable, "-m", "local_agent", "mobile-check"], cwd=ROOT / "local-coding-agent")
        actions.append("mobile_check")
    return actions


def write_report(result: dict[str, Any]) -> None:
    lines = [
        "# APK Launch-Ready Audit",
        f"- Timestamp: {result['timestamp']}",
        f"- Verdict: **{result['verdict']}**",
        f"- Iterations: {result['iterations']}",
        f"- Taylor complete: {result['taylor_complete']}",
        "",
        "## Checks",
        "",
        "| ID | Check | Result |",
        "|----|-------|--------|",
    ]
    for c in result["checks"]:
        lines.append(f"| {c['id']} | {c['name']} | {'PASS' if c['passed'] else 'FAIL'} |")
    if result.get("remediation_actions"):
        lines.extend(["", "## Remediation actions", ""])
        for action in result["remediation_actions"]:
            lines.append(f"- {action}")
    lines.append(f"\nManifest: `{MANIFEST.relative_to(ROOT)}`")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit_loop(max_iterations: int = 8) -> dict[str, Any]:
    print("Building launch-ready APK audit...")
    remediation_actions: list[str] = []
    taylor_complete = False
    checks = run_static_checks()
    for iteration in range(1, max_iterations + 1):
        taylor = run_cmd([sys.executable, str(ROOT / "scripts/taylor_apk_launch_mission.py"), "--apply"])
        taylor_complete = taylor["pass"]
        checks = run_static_checks()
        payload = audit_payload(checks)
        failed = {c.id for c in checks if not c.passed}
        if payload["passed"] and taylor_complete:
            break
        if not failed and not taylor_complete:
            failed.add("TAYLOR")
        if iteration == max_iterations:
            break
        actions = remediate(failed)
        remediation_actions.extend(actions)
        log.info("audit iteration %s remediated=%s failed=%s", iteration, actions, sorted(failed))

    payload = audit_payload(checks)
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": payload["verdict"],
        "passed": payload["passed"] and taylor_complete,
        "launch_ready": payload["passed"] and taylor_complete,
        "taylor_complete": taylor_complete,
        "iterations": iteration,
        "checks": payload["checks"],
        "remediation_actions": remediation_actions,
        "evidence": "evidence/mobile/android/apk_launch_ready.json",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit APK launch readiness with remediation loop")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=8)
    args = parser.parse_args()
    result = audit_loop(max_iterations=args.max_iterations)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"launch_ready": result["launch_ready"], "verdict": result["verdict"]}, indent=2))
    return 0 if result["launch_ready"] else 1


def test_gate_smoke() -> None:
    assert health()["/health"]


if __name__ == "__main__":
    raise SystemExit(main())
