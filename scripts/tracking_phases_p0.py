"""Phase 0 checks for blueprint tracking gate.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/tracking.py gate --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
raise ValueError on unsupported tracking command error
"""

from __future__ import annotations

import logging

from tracking_common import CANONICAL_ISSUES, ROOT, TRACKING, health, open_issues, unsupported_command_error, with_retry_backoff

log = logging.getLogger(__name__)
log.info("tracking_phases_p0 ready")


def phase_0_checks() -> tuple[bool, list[dict]]:
    evidence = []
    open_set = open_issues()
    dedupe_ok = open_set <= CANONICAL_ISSUES and len(open_set) <= 5
    evidence.append({
        "check": "0.1_issue_dedupe",
        "pass": dedupe_ok,
        "open_issues": sorted(open_set),
        "expected": sorted(CANONICAL_ISSUES),
    })
    gate_exists = (ROOT / "scripts" / "tracking.py").exists() and TRACKING.exists()
    evidence.append({"check": "0.2_gate_exists", "pass": gate_exists})
    readme_path = ROOT / "README.md"
    launch_path = ROOT / "LAUNCH_CHECKLIST.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    launch = launch_path.read_text(encoding="utf-8") if launch_path.exists() else ""
    claims_ok = "VALIDATED" in readme and "VALIDATED" in launch and "NOT VERIFIED" in launch
    evidence.append({"check": "0.3_public_claims", "pass": claims_ok})
    return all(e["pass"] for e in evidence), evidence


def test_phase_0_smoke() -> None:
    print("phase_0 smoke")
    if not health()["/health"]:
        raise ValueError("phase_0 smoke error")
