#!/usr/bin/env python3
"""
Refresh auto-generated LIVE STATUS sections in README files.

Called by agent_shadow_worker.py on every run (default). Edits only content
between SHADOW_WORKER_STATUS markers — never touches prose outside markers.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "docs" / "agent_audit_log"
MARKER_BEGIN = "<!-- SHADOW_WORKER_STATUS:BEGIN -->"
MARKER_END = "<!-- SHADOW_WORKER_STATUS:END -->"

TARGETS = [
    REPO / "README.md",
    AUDIT / "README.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def read_txt(path: Path) -> str | None:
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def gate_summary() -> dict[str, Any]:
    out: dict[str, Any] = {"exit_code": None, "phase_0": "?", "phase_1": "?", "open_issues": []}
    try:
        r = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "tracking.py"), "gate"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=90,
        )
        out["exit_code"] = r.returncode
        body = r.stdout + r.stderr
        if '"phase_0_pass": true' in body or '"phase_0_pass": True' in body:
            out["phase_0"] = "PASS"
        elif '"phase_0_pass": false' in body:
            out["phase_0"] = "FAIL"
        if '"phase_1_pass": true' in body or '"phase_1_pass": True' in body:
            out["phase_1"] = "PASS"
        elif '"phase_1_pass": false' in body:
            out["phase_1"] = "FAIL"
        m = re.search(r'"open_issues":\s*\[([^\]]*)\]', body)
        if m:
            nums = re.findall(r"\d+", m.group(1))
            out["open_issues"] = [int(x) for x in nums]
    except (subprocess.TimeoutExpired, OSError):
        out["error"] = "gate timeout"
    return out


def collect_status() -> dict[str, Any]:
    index = load_json(AUDIT / "index.json") or {}
    activity = load_json(AUDIT / "state" / "activity.json") or {}
    benchmark = load_json(REPO / "manifest" / "ecosystem_gather_benchmark.json") or {}
    wasm = load_json(REPO / "manifest" / "wasm_size.json") or {}

    sessions = index.get("sessions", {})
    total_entries = sum(s.get("entry_count", 0) for s in sessions.values())

    return {
        "updated_at": utc_now(),
        "last_activity_utc": activity.get("last_activity_utc", "never"),
        "session_entry_count": total_entries,
        "repo_snapshot_id": read_txt(AUDIT / "repo_snapshots" / "LATEST.txt"),
        "ecosystem_run_id": read_txt(AUDIT / "ecosystem_knowledge" / "LATEST.txt"),
        "ecosystem_repos": load_json(AUDIT / "ecosystem_knowledge" / "manifest.json") or {},
        "benchmark": benchmark,
        "wasm_size_kb": wasm.get("size_kb"),
        "wasm_target_met": wasm.get("met"),
        "gate": gate_summary(),
    }


def format_audit_readme_block(s: dict[str, Any]) -> str:
    eco = s.get("ecosystem_repos", {})
    bench = s.get("benchmark", {})
    gate = s.get("gate", {})
    timings = bench.get("timings_s", {})
    sla_met = bench.get("sla_met", {})

    lines = [
        MARKER_BEGIN,
        "",
        f"_Auto-updated by `scripts/agent_shadow_worker.py` — {s['updated_at']}_",
        "",
        "## Live status",
        "",
        "| Signal | Value |",
        "|--------|-------|",
        f"| Last agent activity | `{s.get('last_activity_utc', 'unknown')}` |",
        f"| Session entries (index) | {s.get('session_entry_count', 0)} |",
        f"| Latest repo snapshot | `{s.get('repo_snapshot_id') or 'none'}` |",
        f"| Latest ecosystem run | `{s.get('ecosystem_run_id') or 'none'}` |",
        f"| Ecosystem repos scanned | {eco.get('repo_count', '—')} |",
        f"| Ecosystem gather time | {timings.get('total_s', '—')}s (SLA met: {sla_met.get('total_under_cap', '—')}) |",
        f"| WASM size | {s.get('wasm_size_kb', '—')} KB (target met: {s.get('wasm_target_met', '—')}) |",
        f"| Blueprint Phase 0 | {gate.get('phase_0', '?')} |",
        f"| Blueprint Phase 1 | {gate.get('phase_1', '?')} |",
        f"| Open issues | {gate.get('open_issues') or '—'} |",
        "",
        "**Shadow worker (run every turn / cron):**",
        "",
        "```bash",
        "python3 scripts/agent_shadow_worker.py run    # heartbeat + README refresh",
        "python3 scripts/agent_shadow_worker.py run --ecosystem --snapshot  # full refresh",
        "python3 scripts/agent_shadow_worker.py install-cron",
        "```",
        "",
        MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def format_root_readme_block(s: dict[str, Any]) -> str:
    gate = s.get("gate", {})
    lines = [
        MARKER_BEGIN,
        "",
        f"**Live audit & blueprint status** — _auto-updated {s['updated_at']}_",
        "",
        "| | |",
        "|---|---|",
        f"| Agent audit log | [`docs/agent_audit_log/`](docs/agent_audit_log/) |",
        f"| Latest ecosystem report | run `{s.get('ecosystem_run_id') or 'none'}` |",
        f"| Blueprint gate | Phase 0: **{gate.get('phase_0', '?')}** · Phase 1: **{gate.get('phase_1', '?')}** · open: {gate.get('open_issues') or '—'} |",
        f"| WASM | {s.get('wasm_size_kb', '—')} KB (target &lt;100 KB met: {s.get('wasm_target_met', '—')}) |",
        "",
        "End of every agent turn: `python3 scripts/agent_shadow_worker.py run`",
        "",
        MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def patch_file(path: Path, new_block: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(new_block.strip(), text)
    else:
        # Insert after first heading block
        if path.name == "README.md" and path.parent == REPO:
            insert_after = "Formally verifiable programming language"
            idx = text.find(insert_after)
            if idx == -1:
                updated = new_block + "\n" + text
            else:
                line_end = text.find("\n", idx)
                updated = text[: line_end + 1] + "\n" + new_block + "\n" + text[line_end + 1 :]
        else:
            updated = new_block + "\n" + text
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def update_readmes() -> dict[str, Any]:
    status = collect_status()
    results: dict[str, Any] = {"updated_at": status["updated_at"], "files": {}}

    audit_block = format_audit_readme_block(status)
    root_block = format_root_readme_block(status)

    results["files"]["docs/agent_audit_log/README.md"] = patch_file(
        AUDIT / "README.md", audit_block
    )
    results["files"]["README.md"] = patch_file(REPO / "README.md", root_block)
    return results


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Update README live-status markers")
    p.add_argument("--json", action="store_true", help="print result JSON only")
    args = p.parse_args()

    result = update_readmes()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, changed in result["files"].items():
            print(f"{'updated' if changed else 'unchanged'}: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
