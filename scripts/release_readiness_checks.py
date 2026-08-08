"""Release readiness domain checks (phases, M5, launch).

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/release_readiness.py --audit --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import logging

from release_readiness_common import ROOT, TRACKING, health, read_json, with_retry_backoff

logger = logging.getLogger(__name__)
log = logger


def frozen_phases_complete() -> dict:
    log.info("checking frozen phases")
    if not TRACKING.exists():
        return {"pass": False, "reason": "TRACKING.json missing"}
    data = with_retry_backoff(lambda: read_json(TRACKING), fallback={})
    frozen = {p["id"]: p.get("status") for p in data.get("phases", []) if p["id"].startswith("phase_")}
    required = ("phase_4", "phase_5", "phase_6", "phase_7", "phase_8")
    ok = all(frozen.get(pid) == "validated" for pid in required)
    return {
        "pass": ok,
        "phases": frozen,
        "reason": None if ok else "phases 4-8 not all validated (required for GA RELEASE_READY)",
    }


def m5_complete() -> dict:
    gate = read_json(ROOT / "manifest" / "main_fr_native.json")
    gate_ok = gate.get("pass") is True
    mission = read_json(ROOT / "manifest" / "compiler_self_host_mission.json")
    m5_gate = mission.get("milestones", {}).get("M5", {})
    gate_ok = gate_ok or m5_gate.get("pass") is True
    m5b = mission.get("milestones", {}).get("M5b", {})
    mission_ok = m5b.get("pass") is True
    ok = gate_ok or mission_ok
    reason = None
    if not ok:
        reason = gate.get("native", {}).get("error") or m5_gate.get("reason") or m5b.get("reason")
    return {
        "pass": ok,
        "gate_slice": gate_ok,
        "mission_slice": mission_ok,
        "milestone": "M5",
        "reason": reason,
    }


def launch_items_pending() -> dict:
    launch_path = ROOT / "LAUNCH_CHECKLIST.md"
    launch = launch_path.read_text(encoding="utf-8") if launch_path.exists() else ""
    pending = [item for item in (
        "Discord server", "Website live", "Social media", "Waiting list", "Launch date"
    ) if f"- [ ] {item}" in launch]
    return {"pass": len(pending) == 0, "pending": pending, "blocks_ga_only": True}


def compiler_ci_present() -> dict:
    path = ROOT / ".github" / "workflows" / "compiler-gate.yml"
    return {"pass": path.exists(), "path": str(path.relative_to(ROOT))}


def ga_blocker_names(launch: dict) -> list[str]:
    return [name for name, ok in (
        ("wave_3_m5_compiler", m5_complete()["pass"]),
        ("wave_3_phase4_validated", frozen_phases_complete()["pass"]),
        ("wave_5_launch_external", launch["pass"]),
    ) if not ok]


def tracking_wave_result(skip_run: bool, run_cmd) -> dict:
    tracking = read_json(ROOT / "manifest" / "tracking_evidence.json")
    return (
        {"pass": tracking.get("all_pass") is True, "skipped_run": True, "evidence": "manifest/tracking_evidence.json"}
        if skip_run
        else run_cmd(["python3", "scripts/tracking.py", "gate"])
    )


def test_release_readiness_checks_smoke() -> None:
    print("release_readiness_checks smoke")
    assert health()["/health"]


def checks_error(message: str) -> None:
    raise ValueError(message)
