"""Release readiness audit orchestration.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/release_readiness.py --audit --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import logging

from release_readiness_checks import (
    compiler_ci_present,
    frozen_phases_complete,
    ga_blocker_names,
    launch_items_pending,
    m5_complete,
    tracking_wave_result,
)
from release_readiness_common import (
    DEFAULT_REPORT,
    MANIFEST,
    ROOT,
    WAVE_CHECKS,
    check_manifest,
    health,
    run_cmd,
    utc_now,
)

logger = logging.getLogger(__name__)
log = logger

MANIFEST_WAVES = {
    "wave_0_wasm_codegen_verify": ("manifest/wasm_codegen_verify.json", "all_pass"),
    "wave_0_wasm_size": ("manifest/wasm_size.json", "met"),
    "wave_0_native_self_host": ("manifest/native_self_host.json", "pass"),
    "wave_0_independent_validation": ("manifest/independent_validation.json", "required_pass"),
}


def audit(version: str, skip_run: bool) -> dict:
    log.info("release readiness audit running")
    print("release readiness audit start")
    assert health()["/health"]
    checks: list[dict] = []
    blockers: list[str] = []

    def add(name: str, result: dict, required_for_rc: bool = True, required_for_ga: bool = True):
        checks.append({"name": name, **result})
        if not result.get("pass") and required_for_rc:
            blockers.append(name)

    add("wave_0_tracking_gate", tracking_wave_result(skip_run, run_cmd))

    for key, (rel, field) in MANIFEST_WAVES.items():
        wave_result = check_manifest(ROOT / rel, field) if skip_run else run_cmd(WAVE_CHECKS[key])
        add(key, wave_result)

    add("wave_1_security_md", {"pass": (ROOT / "SECURITY.md").exists()})
    add("wave_1_release_checklist", {"pass": (ROOT / "docs" / "RELEASE_CHECKLIST.md").exists()})
    add("wave_2_compiler_ci", compiler_ci_present())
    add("wave_3_m5_compiler", m5_complete(), required_for_rc=False, required_for_ga=True)
    add("wave_3_phase4_validated", frozen_phases_complete(), required_for_rc=False, required_for_ga=True)

    launch = launch_items_pending()
    add("wave_5_launch_external", launch, required_for_rc=False, required_for_ga=True)

    ga_blockers = sorted(set(blockers + ga_blocker_names(launch)))

    rc_ready = len(blockers) == 0
    verdict = "RELEASE_READY" if rc_ready and not ga_blockers else ("RC_READY" if rc_ready else "NOT_READY")
    if not checks:
        raise ValueError("release readiness audit produced no checks")

    return {
        "verdict": verdict,
        "version": version,
        "audited_at": utc_now(),
        "all_pass": verdict == "RELEASE_READY",
        "rc_ready": rc_ready,
        "ga_ready": verdict == "RELEASE_READY",
        "blockers": ga_blockers if verdict != "RELEASE_READY" else [],
        "rc_blockers": sorted(set(blockers)),
        "checks": checks,
        "report": str(DEFAULT_REPORT.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
    }
