#!/usr/bin/env python3
"""
Audit WASM size history before any #48 remediation.

Owner directive: a prior chat/session may have already hit sub-100 KB (e.g. ~98 KB).
Workers MUST run this audit first and reconcile branch evidence before optimizing.

Writes:
  manifest/wasm_size_history.json
  audit_reports/wasm_size_history_report.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_OUT = ROOT / "manifest" / "wasm_size_history.json"
REPORT_OUT = ROOT / "audit_reports" / "wasm_size_history_report.md"

# Branches to inspect (owner + prior agent work)
DEFAULT_REFS = [
    "HEAD",
    "cursor/frontier-syntax-cycle1-e39f",
    "cursor/wasm-size-phase3-f519",
    "cursor/blueprint-v2-wasm-llm-f519",
    "origin/cursor/wasm-size-phase3-f519",
    "origin/cursor/blueprint-v2-wasm-llm-f519",
]

SEARCH_PATHS = [
    ROOT / "docs" / "agent_audit_log",
    ROOT / "agent-legal-record",
    ROOT / "audit_reports",
]

SIZE_CLAIM_RE = re.compile(
    r"(?P<kb>\d{2,3}(?:\.\d)?)\s*KB|met[\"']?\s*:\s*true|under\s+100|sub-?100",
    re.IGNORECASE,
)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def current_ref() -> str:
    r = git("rev-parse", "--abbrev-ref", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def resolve_ref(ref: str) -> str | None:
    r = git("rev-parse", "--verify", ref)
    return r.stdout.strip() if r.returncode == 0 else None


def manifest_at(ref: str) -> dict[str, Any] | None:
    r = git("show", f"{ref}:manifest/wasm_size.json")
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    data["_ref"] = ref
    return data


def history_commits(limit: int = 50) -> list[dict[str, Any]]:
    r = git("log", "--all", f"-{limit}", "--format=%H %s", "--", "manifest/wasm_size.json")
    if r.returncode != 0:
        return []
    entries: list[dict[str, Any]] = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition(" ")
        m = manifest_at(sha)
        if not m:
            continue
        entries.append(
            {
                "commit": sha[:12],
                "subject": subject.strip(),
                "size_kb": m.get("size_kb"),
                "met": m.get("met"),
                "git_sha": m.get("git_sha"),
            }
        )
    return entries


def scan_text_claims() -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for base in SEARCH_PATHS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".md", ".json", ".jsonl", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "wasm" not in text.lower() and "kb" not in text.lower():
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if not SIZE_CLAIM_RE.search(line):
                    continue
                if "wasm" not in line.lower() and "kb" not in line.lower():
                    continue
                claims.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": i,
                        "excerpt": line.strip()[:200],
                    }
                )
    return claims[:80]


def build_audit(refs: list[str]) -> dict[str, Any]:
    ref_snapshots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        resolved = resolve_ref(ref)
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        m = manifest_at(resolved)
        if m:
            ref_snapshots.append(
                {
                    "ref": ref,
                    "commit": resolved[:12],
                    "size_kb": m.get("size_kb"),
                    "met": m.get("met"),
                    "measured_at": m.get("measured_at"),
                    "git_sha": m.get("git_sha"),
                }
            )

    history = history_commits()
    claims = scan_text_claims()
    best_met = [s for s in ref_snapshots if s.get("met") is True]
    best_met.sort(key=lambda x: float(x.get("size_kb") or 999))

    current = manifest_at("HEAD")
    current_met = bool(current and current.get("met"))
    historical_met_elsewhere = bool(best_met) and not current_met

    recommendation = "measure_current"
    if historical_met_elsewhere:
        best = best_met[0]
        recommendation = (
            f"RECONCILE_BEFORE_FIX: target already met on {best['ref']} "
            f"({best['size_kb']} KB, commit {best['commit']}). "
            "Cherry-pick/merge wasm-slim changes before re-optimizing #48."
        )
    elif current_met:
        recommendation = "CURRENT_BRANCH_MET: verify with independent validator; do not re-optimize."

    return {
        "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "auditor": "scripts/audit_wasm_size_history.py",
        "owner_directive": (
            "Check git history and sibling branches for prior sub-100 KB WASM work "
            "(owner recalls ~98 KB in a prior chat) before any #48 remediation."
        ),
        "current_ref": current_ref(),
        "current_manifest": {
            "size_kb": current.get("size_kb") if current else None,
            "met": current.get("met") if current else None,
            "git_sha": current.get("git_sha") if current else None,
        },
        "ref_snapshots": ref_snapshots,
        "commit_history": history,
        "text_claims_sample": claims,
        "best_met_snapshot": best_met[0] if best_met else None,
        "historical_met_elsewhere": historical_met_elsewhere,
        "audit_first_required": True,
        "block_optimize_until_reconciled": historical_met_elsewhere,
        "recommendation": recommendation,
    }


def write_report(data: dict[str, Any]) -> None:
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# WASM Size History Audit",
        "",
        f"**Audited:** {data['audited_at']}  ",
        f"**Current ref:** `{data['current_ref']}`  ",
        "",
        "## Owner directive",
        "",
        data["owner_directive"],
        "",
        "## Current branch",
        "",
        f"| size_kb | met | git_sha |",
        f"|---------|-----|---------|",
    ]
    cm = data["current_manifest"]
    lines.append(f"| {cm.get('size_kb')} | {cm.get('met')} | {cm.get('git_sha')} |")
    lines.extend(["", "## Ref snapshots", "", "| ref | commit | size_kb | met |", "|-----|--------|---------|-----|"])
    for s in data["ref_snapshots"]:
        lines.append(f"| `{s['ref']}` | `{s['commit']}` | {s.get('size_kb')} | {s.get('met')} |")

    if data.get("best_met_snapshot"):
        b = data["best_met_snapshot"]
        lines.extend(
            [
                "",
                "## Best historical `met: true`",
                "",
                f"- **Ref:** `{b['ref']}` @ `{b['commit']}`",
                f"- **Size:** {b.get('size_kb')} KB (target 100 KB)",
            ]
        )

    lines.extend(["", "## Recommendation", "", f"**{data['recommendation']}**", ""])
    if data.get("block_optimize_until_reconciled"):
        lines.extend(
            [
                "> WasmSizer: **do not run optimize_wasm_size** until wasm-slim changes from the "
                "historical branch are merged/reconciled on the current branch.",
                "",
            ]
        )

    lines.extend(["## Commit history (manifest/wasm_size.json)", ""])
    for h in data.get("commit_history", [])[:15]:
        flag = "PASS" if h.get("met") else "FAIL"
        lines.append(f"- `{h['commit']}` — {h.get('size_kb')} KB ({flag}) — {h.get('subject', '')[:60]}")

    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Audit WASM size history before #48 work")
    p.add_argument("--refs", nargs="*", default=DEFAULT_REFS, help="git refs to inspect")
    p.add_argument("--json-only", action="store_true")
    args = p.parse_args()

    data = build_audit(args.refs)
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_report(data)

    if not args.json_only:
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
