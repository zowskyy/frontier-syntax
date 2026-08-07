#!/usr/bin/env python3
"""
Taylor Ops Issue Closer — independent validator that closes canonical GitHub issues.

Each Taylor worker owns specific blueprint issues (manifest/canonical_issues.json).
After a worker runs its verification commands, this script:
  1. Re-runs verification as independent validator (not trusting worker stdout alone)
  2. Checks evidence manifests and phase dependencies
  3. Closes eligible issues via `gh issue close` with evidence comment (--apply)

Dry-run by default. Use --apply to mutate GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "manifest" / "canonical_issues.json"
STATUS = ROOT / "manifest" / "issue_closure_status.json"
REPORT = ROOT / "audit_reports" / "issue_closure_report.md"

VALIDATOR = "Taylor Ops Independent Validator (scripts/taylor_issue_closer.py)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def open_issues() -> set[int]:
    r = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--json", "number"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return set()
    return {i["number"] for i in json.loads(r.stdout)}


def run_cmd(cmd: list[str], timeout: int = 300) -> dict[str, Any]:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {
            "command": " ".join(cmd),
            "pass": r.returncode == 0,
            "exit_code": r.returncode,
            "output_tail": (r.stdout + r.stderr)[-1200:],
        }
    except FileNotFoundError as e:
        return {"command": " ".join(cmd), "pass": False, "exit_code": 127, "output_tail": str(e)}
    except subprocess.TimeoutExpired:
        return {"command": " ".join(cmd), "pass": False, "exit_code": 124, "output_tail": "timeout"}


def check_native_self_host() -> dict[str, Any]:
    """Phase 1.3 — wasmtime + Frontier compiler WASM (no bootstrap.run cargo)."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_native_self_host.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    try:
        data = json.loads(r.stdout)
        passed = bool(data.get("pass"))
    except json.JSONDecodeError:
        passed = False
        data = {"error": (r.stdout + r.stderr)[-400:]}
    return {
        "pass": passed,
        "reason": None if passed else "Native self-host not yet passing — see manifest/native_self_host.json",
        "manifest": "manifest/native_self_host.json",
        "detail": data,
    }


def read_manifest_field(path: str, field: str) -> tuple[bool, Any]:
    p = ROOT / path
    if not p.exists():
        return False, None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, None
    return bool(data.get(field)), data.get(field)


def evaluate_issue(
    issue_key: str,
    spec: dict[str, Any],
    *,
    open_set: set[int],
    closed_set: set[int],
) -> dict[str, Any]:
    num = spec["github"]
    result: dict[str, Any] = {
        "issue": num,
        "key": issue_key,
        "phase": spec.get("phase"),
        "worker": spec.get("worker"),
        "title": spec.get("title"),
        "open": num in open_set,
        "eligible": False,
        "closed": False,
        "steps": [],
        "blockers": [],
    }

    if num not in open_set:
        result["eligible"] = False
        result["already_closed"] = True
        return result

    for dep in spec.get("blocked_until_issues_closed", []):
        if dep in open_set:
            result["blockers"].append(f"dependency issue #{dep} still open")

    if spec.get("requires_native_self_host"):
        native = check_native_self_host()
        result["steps"].append({"check": "native_self_host", **native})
        if not native["pass"]:
            result["blockers"].append(native["reason"])

    for cmd in spec.get("verification_commands", []):
        step = run_cmd(cmd)
        step["check"] = "verification_command"
        result["steps"].append(step)
        if not step["pass"]:
            result["blockers"].append(f"verification failed: {step['command']}")

    manifest_path = spec.get("evidence_manifest")
    if manifest_path:
        field = spec.get("evidence_field", "pass")
        ok, val = read_manifest_field(manifest_path, field)
        result["steps"].append(
            {
                "check": "evidence_manifest",
                "path": manifest_path,
                "field": field,
                "value": val,
                "pass": ok,
            }
        )
        if not ok:
            result["blockers"].append(f"manifest {manifest_path} field {field} not satisfied")

    result["eligible"] = not result["blockers"]
    return result


def build_close_comment(issue: dict[str, Any], run_id: str) -> str:
    lines = [
        f"Closed by **{VALIDATOR}** (run `{run_id}`).",
        "",
        f"**Phase:** {issue.get('phase')}  ",
        f"**Owner worker:** {issue.get('worker')}  ",
        "",
        "## Verification evidence",
        "",
    ]
    for s in issue.get("steps", []):
        if s.get("check") == "verification_command":
            status = "PASS" if s.get("pass") else "FAIL"
            lines.append(f"- `{status}` `{s.get('command')}`")
        elif s.get("check") == "evidence_manifest":
            status = "PASS" if s.get("pass") else "FAIL"
            lines.append(f"- `{status}` `{s.get('path')}` → `{s.get('field')}` = `{s.get('value')}`")
    lines.extend(
        [
            "",
            "See `manifest/issue_closure_status.json` and `audit_reports/issue_closure_report.md`.",
            "",
            "_Independent validator run — not self-closed by implementer agent._",
        ]
    )
    return "\n".join(lines)


def close_issue(num: int, comment: str) -> dict[str, Any]:
    r = subprocess.run(
        ["gh", "issue", "close", str(num), "--comment", comment],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "issue": num,
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "output": (r.stdout + r.stderr)[-600:],
    }


def audit(
    *,
    worker: str | None = None,
    apply: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    reg = load_registry()
    open_set = open_issues()
    closed_candidates: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    closed_set = set()  # issues we close this run (for dependency checks within batch)

    for key, spec in reg.get("issues", {}).items():
        if worker and spec.get("worker") != worker:
            continue
        ev = evaluate_issue(key, spec, open_set=open_set, closed_set=closed_set)
        all_results.append(ev)
        if ev.get("eligible"):
            closed_candidates.append(ev)

    closed_actions: list[dict[str, Any]] = []
    if apply:
        # Re-evaluate in phase order so dependencies clear within one run
        for key in sorted(reg.get("issues", {}).keys(), key=lambda k: reg["issues"][k].get("phase", "")):
            spec = reg["issues"][key]
            if worker and spec.get("worker") != worker:
                continue
            num = spec["github"]
            if num not in open_set:
                continue
            ev = evaluate_issue(key, spec, open_set=open_set, closed_set=closed_set)
            if not ev.get("eligible"):
                continue
            comment = build_close_comment(ev, run_id)
            action = close_issue(num, comment)
            action["worker"] = spec.get("worker")
            action["phase"] = spec.get("phase")
            closed_actions.append(action)
            if action["pass"]:
                open_set.discard(num)
                closed_set.add(num)
                ev["closed"] = True

    summary = {
        "run_id": run_id,
        "audited_at": utc_now(),
        "validator": VALIDATOR,
        "apply": apply,
        "worker_filter": worker,
        "open_before": sorted(open_set | {r["issue"] for r in all_results if r.get("open")}),
        "eligible_to_close": [r["issue"] for r in all_results if r.get("eligible")],
        "closed_this_run": [a["issue"] for a in closed_actions if a.get("pass")],
        "still_open": sorted(open_issues()),
        "issues": all_results,
        "close_actions": closed_actions,
    }

    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(summary)
    return summary


def write_report(summary: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Taylor Ops Issue Closure Report",
        "",
        f"**Run ID:** `{summary['run_id']}`  ",
        f"**Audited:** {summary['audited_at']}  ",
        f"**Apply:** {summary.get('apply')}  ",
        f"**Validator:** {summary.get('validator')}  ",
        "",
        "## Summary",
        "",
        f"| Eligible to close | Closed this run | Still open |",
        f"|-------------------|-----------------|------------|",
        f"| {len(summary.get('eligible_to_close', []))} | {len(summary.get('closed_this_run', []))} | {len(summary.get('still_open', []))} |",
        "",
        "## Per-issue status",
        "",
        "| Issue | Worker | Phase | Open | Eligible | Blockers |",
        "|-------|--------|-------|------|----------|----------|",
    ]
    for r in summary.get("issues", []):
        blockers = "; ".join(r.get("blockers", [])) or "—"
        lines.append(
            f"| #{r['issue']} | {r.get('worker')} | {r.get('phase')} | "
            f"{'yes' if r.get('open') else 'no'} | {'yes' if r.get('eligible') else 'no'} | {blockers[:80]} |"
        )
    lines.append("")
    if summary.get("closed_this_run"):
        lines.append("## Closed this run")
        lines.append("")
        for n in summary["closed_this_run"]:
            lines.append(f"- #{n}")
        lines.append("")
    lines.append(f"Manifest: `{STATUS.relative_to(ROOT)}`")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def cmd_audit(args: argparse.Namespace) -> int:
    summary = audit(worker=args.worker, apply=False)
    print(json.dumps({
        "eligible": summary["eligible_to_close"],
        "still_open": summary["still_open"],
        "report": str(REPORT.relative_to(ROOT)),
        "manifest": str(STATUS.relative_to(ROOT)),
    }, indent=2))
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    summary = audit(worker=args.worker, apply=args.apply, run_id=args.run_id)
    print(json.dumps({
        "apply": args.apply,
        "eligible": summary["eligible_to_close"],
        "closed": summary["closed_this_run"],
        "still_open": summary["still_open"],
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    if STATUS.exists():
        print(STATUS.read_text(encoding="utf-8"))
        return 0
    print("{}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Taylor Ops — independent issue closer")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="Dry-run: which issues are eligible to close")
    a.add_argument("--worker", help="Filter to one worker id (e.g. W2_CompilerCore)")
    a.set_defaults(func=cmd_audit)

    c = sub.add_parser("close", help="Close eligible issues")
    c.add_argument("--apply", action="store_true", help="Actually close on GitHub")
    c.add_argument("--worker", help="Filter to one worker id")
    c.add_argument("--run-id", help="Run id for evidence comments")
    c.set_defaults(func=cmd_close)

    s = sub.add_parser("status", help="Print last closure manifest")
    s.set_defaults(func=cmd_status)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
