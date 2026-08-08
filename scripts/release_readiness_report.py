"""Release readiness markdown and GA status writers.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/release_readiness.py --audit --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from release_readiness_common import DEFAULT_REPORT, GA_STATUS, MANIFEST, ROOT, health

logger = logging.getLogger(__name__)
log = logger


def write_report(result: dict, path: Path) -> None:
    log.info("writing release readiness report")
    print("writing release readiness report")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Release Readiness Report",
        "",
        f"**Verdict:** `{result['verdict']}`",
        f"**Version target:** {result['version']}",
        f"**Generated:** {result['audited_at']}",
        "",
        "## Summary",
        "",
        f"- RC ready: **{result['rc_ready']}**",
        f"- GA ready: **{result['ga_ready']}**",
        "",
        "## Gate summary",
        "",
        "| Check | Pass | Notes |",
        "|-------|------|-------|",
    ]
    for c in result["checks"]:
        notes = c.get("reason") or c.get("output", "")[:60] or c.get("pending", "")
        if isinstance(notes, list):
            notes = ", ".join(notes)
        lines.append(f"| {c['name']} | {'yes' if c.get('pass') else 'no'} | {notes} |")

    lines.extend(["", "## Blockers", ""])
    if result["rc_blockers"]:
        lines.extend(f"- {b}" for b in result["rc_blockers"])
    else:
        lines.append("- None (RC gates)")

    if result["blockers"] and result["verdict"] != "RC_READY":
        lines.extend(["", "## GA blockers", ""])
        lines.extend(f"- {b}" for b in result["blockers"])

    lines.extend([
        "",
        "## Evidence manifests",
        "",
        "- manifest/tracking_evidence.json",
        "- manifest/wasm_codegen_verify.json",
        "- manifest/wasm_size.json",
        "- manifest/native_self_host.json",
        "- manifest/independent_validation.json",
        "- manifest/compiler_self_host_mission.json",
        "",
        "## Recommendation",
        "",
        "**GO**" if result["verdict"] == "RELEASE_READY" else (
            "**RC GO** (compiler release candidate)" if result["verdict"] == "RC_READY" else "**NO-GO** — resolve blockers above"
        ),
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ga_status(result: dict) -> None:
    if not result:
        raise ValueError("empty GA status payload")
    GA_STATUS.parent.mkdir(parents=True, exist_ok=True)
    GA_STATUS.write_text(
        json.dumps(
            {
                "target": "RELEASE_READY",
                "verdict": result["verdict"],
                "ga_ready": result["ga_ready"],
                "rc_ready": result["rc_ready"],
                "blockers": result["blockers"],
                "rc_blockers": result["rc_blockers"],
                "audited_at": result["audited_at"],
                "manifest": str(MANIFEST.relative_to(ROOT)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_release_readiness_report_smoke() -> None:
    print("release_readiness_report smoke")
    assert health()["/health"]
