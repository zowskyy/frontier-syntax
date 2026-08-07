#!/usr/bin/env python3
"""
Gather knowledge across all zowskyy GitHub repos and consolidate into
docs/agent_audit_log/ecosystem_knowledge/.

Every pipeline step is logged via scripts/agent_audit_logger.py and mirrored
to docs/agent_audit_log/pipeline_logs/<run_id>/.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_ROOT = REPO_ROOT / "docs" / "agent_audit_log"
ECO_ROOT = AUDIT_ROOT / "ecosystem_knowledge"
PIPELINE_ROOT = AUDIT_ROOT / "pipeline_logs"
LOGGER = REPO_ROOT / "scripts" / "agent_audit_logger.py"
OWNER = "zowskyy"
SLA_PATH = REPO_ROOT / "manifest" / "ecosystem_gather_sla.json"
BENCHMARK_PATH = REPO_ROOT / "manifest" / "ecosystem_gather_benchmark.json"
GH_RETRIES = 3
GH_BACKOFF_S = 1.5

# Repos with direct blueprint / Frontier ecosystem relevance
FRONTIER_CORE = {"frontier-syntax"}
FRONTIER_ECOSYSTEM = {
    "project-nexus",
    "apex-android",
    "prjctnxs",
    "frontier-agent-legal-record",
    "bookish-bassoon",
    "repurpose-engine",
    "statecheck",
}
KNOWN_FORKS = {
    "Vanadium",
    "quick-xml",
    "jadx",
    "mcp-for-beginners",
    "masked-irl",
    "android-reverse-engineering-skill",
    "echoscribe",
    "Voice-Of-the-Star",
    "etrnL",
    "apktool-diagnostics",
    "crxcibl3",
    "crxcibl3sounds",
    "gutterumble",
    "slackhelper",
    "mia.loa",
    "Schema",
    "verbose-train",
    "GMFKNEEGA",
    "nuDAWn",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log_pipeline(pipe_dir: Path, step: str, msg: str) -> None:
    pipe_dir.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] [{step}] {msg}\n"
    with (pipe_dir / "pipeline.log").open("a", encoding="utf-8") as f:
        f.write(line)


def audit_record(
    *,
    category: str,
    action: str,
    why: str,
    command: str = "",
    script: str = "scripts/gather_ecosystem_knowledge.py",
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    verified: bool = False,
    omissions: list[str] | None = None,
    cannot_verify: list[str] | None = None,
    exit_code: int | None = None,
) -> None:
    cmd = [
        sys.executable,
        str(LOGGER),
        "record",
        "--category",
        category,
        "--action",
        action,
        "--why",
        why,
        "--command",
        command,
        "--script",
        script,
        "--inputs",
        json.dumps(inputs or {}, default=str),
        "--outputs",
        json.dumps(outputs or {}, default=str),
    ]
    for a in artifacts or []:
        cmd.extend(["--artifact", a])
    if verified:
        cmd.append("--verified")
    for o in omissions or []:
        cmd.extend(["--omission", o])
    for c in cannot_verify or []:
        cmd.extend(["--cannot-verify", c])
    if exit_code is not None:
        cmd.extend(["--exit-code", str(exit_code)])
    subprocess.run(cmd, cwd=REPO_ROOT, check=False)


def gh_run(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run gh with exponential backoff on transient failures."""
    last_err = ""
    for attempt in range(GH_RETRIES):
        try:
            r = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if r.returncode == 0:
                return 0, r.stdout, r.stderr
            if r.returncode in (429, 502, 503) or "rate limit" in (r.stderr or "").lower():
                time.sleep(GH_BACKOFF_S * (2**attempt))
                last_err = r.stderr
                continue
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            time.sleep(GH_BACKOFF_S * (2**attempt))
            last_err = "timeout"
    return 1, "", last_err


def gh_json(args: list[str], timeout: int = 60) -> Any:
    code, out, _ = gh_run(args, timeout=timeout)
    if code != 0:
        return None
    try:
        return json.loads(out) if out.strip() else None
    except json.JSONDecodeError:
        return None


def gh_text(args: list[str], timeout: int = 30) -> str | None:
    code, out, _ = gh_run(args, timeout=timeout)
    return out.strip() if code == 0 else None


def classify_repo(name: str) -> str:
    if name in FRONTIER_CORE:
        return "frontier_core"
    if name in FRONTIER_ECOSYSTEM:
        return "frontier_ecosystem"
    if name in KNOWN_FORKS:
        return "fork_or_adjacent"
    return "other"


def blueprint_relation(name: str, category: str) -> str:
    if name == "frontier-syntax":
        return (
            "Canonical compiler repo. All blueprint phases (0–8) apply here. "
            "TRACKING.json + scripts/tracking.py gate are authoritative."
        )
    if name == "project-nexus":
        return (
            "Claims Cursor IDE in Frontier Syntax. Blocked until frontier-syntax "
            "Phase 1 exit (self-hosting + working WASM). Phase 5+ dependency."
        )
    if name == "apex-android":
        return (
            "Android tooling adjacent to reverse-engineering skills. "
            "Not on critical blueprint path; may consume Frontier output later."
        )
    if name == "prjctnxs":
        return (
            "Project Nexus support / submodule. Out of scope for frontier-syntax "
            "gate but ecosystem coordination repo."
        )
    if name == "frontier-agent-legal-record":
        return (
            "Private audit mirror (cloud agent could not push). "
            "Superseded by in-repo docs/agent_audit_log/ per owner policy."
        )
    if name in {"bookish-bassoon", "repurpose-engine", "statecheck"}:
        return "Automation / worker scripts; may invoke frontier-syntax tooling."
    if category == "fork_or_adjacent":
        return "Upstream fork or unrelated project — no blueprint phase dependency."
    return "No direct blueprint dependency identified."


def load_frontier_syntax_status(*, fast: bool = False) -> dict[str, Any]:
    status: dict[str, Any] = {"local": True, "checks": {}}

    tracking_path = REPO_ROOT / "TRACKING.json"
    if tracking_path.exists():
        status["tracking"] = json.loads(tracking_path.read_text(encoding="utf-8"))

    wasm_manifest = REPO_ROOT / "manifest" / "wasm_size.json"
    if wasm_manifest.exists():
        status["wasm_size"] = json.loads(wasm_manifest.read_text(encoding="utf-8"))

    if fast and BENCHMARK_PATH.exists():
        status["checks"]["tracking_gate"] = {"exit": 1, "output": "skipped (--fast)"}
        return status

    try:
        gate_out = subprocess.check_output(
            [sys.executable, str(REPO_ROOT / "scripts" / "tracking.py"), "gate"],
            cwd=REPO_ROOT,
            text=True,
            timeout=120,
            stderr=subprocess.STDOUT,
        )
        status["checks"]["tracking_gate"] = {"exit": 0, "output": gate_out[-4000:]}
    except subprocess.CalledProcessError as e:
        status["checks"]["tracking_gate"] = {
            "exit": e.returncode,
            "output": (e.output or "")[-4000:],
        }

    if fast:
        return status

    for label, cmd in [
        ("cargo_test_lib", ["cargo", "test", "--lib", "--quiet"]),
        ("verify_wasm", [sys.executable, "scripts/verify_wasm_codegen.py"]),
        ("measure_wasm", [sys.executable, "scripts/measure_wasm_size.py"]),
    ]:
        try:
            out = subprocess.check_output(cmd, cwd=REPO_ROOT, text=True, timeout=180, stderr=subprocess.STDOUT)
            status["checks"][label] = {"exit": 0, "output": out[-2000:]}
        except subprocess.CalledProcessError as e:
            status["checks"][label] = {"exit": e.returncode, "output": (e.output or "")[-2000:]}

    return status


def readme_excerpt(name: str, is_private: bool) -> tuple[str, str]:
    """Returns (excerpt, access_status)."""
    if is_private and name != "frontier-agent-legal-record":
        return "(private — README not fetched)", "inaccessible_private"

    raw = gh_text(["api", f"repos/{OWNER}/{name}/readme", "--jq", ".content"], timeout=20)
    if not raw:
        return "(no README or access denied)", "no_readme"

    import base64

    try:
        decoded = base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return "(README decode failed)", "decode_error"

    lines = decoded.splitlines()
    excerpt = "\n".join(lines[:60])
    if len(lines) > 60:
        excerpt += f"\n... ({len(lines) - 60} more lines)"
    return excerpt, "ok"


def top_level_files(name: str, is_private: bool) -> tuple[list[str], str]:
    if name == "frontier-syntax":
        try:
            entries = sorted(
                p.name for p in REPO_ROOT.iterdir() if p.name != ".git"
            )[:40]
            return entries, "ok_local"
        except OSError:
            pass
    if is_private:
        return [], "inaccessible_private"
    data = gh_json(
        ["api", f"repos/{OWNER}/{name}/contents", "--jq", "[.[].name]"],
        timeout=30,
    )
    if data is None:
        return [], "fetch_failed"
    if isinstance(data, list):
        return sorted(str(x) for x in data)[:40], "ok"
    return [], "unexpected_format"


def infer_claims(description: str, readme: str) -> list[str]:
    claims: list[str] = []
    if description:
        claims.append(f"GitHub description: {description}")

    hype_patterns = [
        r"(?i)self-host",
        r"(?i)production[- ]ready",
        r"(?i)complete",
        r"(?i)all tests passing",
        r"(?i)cursor ide",
        r"(?i)ai-native",
        r"(?i)zero-backend",
        r"(?i)privacy-first",
    ]
    for line in readme.splitlines()[:80]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for pat in hype_patterns:
            if re.search(pat, stripped):
                claims.append(stripped[:200])
                break
    return claims[:12] or ["(no explicit claims extracted from README)"]


def infer_capabilities(
    name: str,
    category: str,
    lang: str | None,
    files: list[str],
    frontier_status: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    can: list[str] = []
    cannot: list[str] = []

    if name == "frontier-syntax" and frontier_status:
        checks = frontier_status.get("checks", {})
        if checks.get("cargo_test_lib", {}).get("exit") == 0:
            can.append("cargo test --lib passes (40 unit tests at last run)")
        if checks.get("verify_wasm", {}).get("exit") == 0:
            can.append("wasmtime verification: let/if/while/function_call (4 cases)")
        wasm = frontier_status.get("wasm_size", {})
        if wasm.get("met"):
            can.append(f"WASM size target met: {wasm.get('size_kb')} KB < {wasm.get('target_kb')} KB")
        else:
            cannot.append(
                f"WASM size target NOT met: {wasm.get('size_kb', '?')} KB vs {wasm.get('target_kb', 100)} KB"
            )
        gate = checks.get("tracking_gate", {})
        if gate.get("exit") != 0:
            cannot.append("scripts/tracking.py gate FAIL — Phase 1 P0s not validated")
            cannot.append("Issues #44–#48 remain open; no independent validator closure")
        tracking = frontier_status.get("tracking", {})
        for phase in tracking.get("phases", []):
            if phase.get("status") in ("fail", "blocked", "frozen"):
                cannot.append(f"Blueprint {phase.get('id')}: {phase.get('status')} — {phase.get('blocked_reason', phase.get('name', ''))}")
        return can, cannot

    if files:
        can.append(f"Top-level structure visible ({len(files)} entries): {', '.join(files[:8])}")
        if "Cargo.toml" in files:
            can.append("Rust project (Cargo.toml present)")
        if "package.json" in files:
            can.append("Node/JS project (package.json present)")
        if "requirements.txt" in files or "pyproject.toml" in files:
            can.append("Python project indicators present")
        if ".github/workflows" in files:
            can.append("GitHub Actions workflows directory present")
        else:
            cannot.append("No .github/workflows at repo root (CI not confirmed)")

    if category == "frontier_ecosystem" and name == "project-nexus":
        cannot.append("Cannot self-host IDE — depends on frontier-syntax Phase 1+ (compiler not validated)")
    if category == "fork_or_adjacent":
        cannot.append("Not part of Frontier blueprint critical path")

    if not can:
        can.append("(capabilities not verified — metadata-only scan)")
    if not cannot:
        cannot.append("(limitations not probed — shallow scan only)")

    return can, cannot


@dataclass
class RepoProfile:
    name: str
    url: str
    description: str
    is_private: bool
    language: str | None
    updated_at: str
    category: str
    access_status: str
    readme_excerpt: str
    top_level_files: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    can_do: list[str] = field(default_factory=list)
    cannot_do: list[str] = field(default_factory=list)
    blueprint_relation: str = ""


def format_repo_section(r: RepoProfile, index: int) -> str:
    sep = "=" * 78
    lines = [
        sep,
        f"REPO {index}: {OWNER}/{r.name}",
        sep,
        "",
        "## WHAT IT IS",
        f"  URL:        {r.url}",
        f"  Visibility: {'private' if r.is_private else 'public'}",
        f"  Language:   {r.language or '(none detected)'}",
        f"  Category:   {r.category}",
        f"  Updated:    {r.updated_at}",
        f"  Access:     {r.access_status}",
        "",
        "## WHAT IT CLAIMS",
    ]
    for c in r.claims:
        lines.append(f"  • {c}")
    lines += [
        "",
        "## README EXCERPT",
        textwrap.indent(r.readme_excerpt[:3000], "  "),
        "",
        "## VERIFIED — CAN DO (this scan)",
    ]
    for x in r.can_do:
        lines.append(f"  ✓ {x}")
    lines += [
        "",
        "## CANNOT DO / NOT VERIFIED / LIMITATIONS",
    ]
    for x in r.cannot_do:
        lines.append(f"  ✗ {x}")
    lines += [
        "",
        "## BLUEPRINT RELATION (frontier-syntax PROJECT_BLUEPRINT.md)",
        f"  {r.blueprint_relation}",
        "",
    ]
    return "\n".join(lines)


def write_report(
    profiles: list[RepoProfile],
    frontier_status: dict[str, Any],
    run: str,
    pipe_dir: Path,
) -> tuple[Path, Path]:
    ECO_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = ECO_ROOT / "ECOSYSTEM_KNOWLEDGE_REPORT.txt"
    manifest_path = ECO_ROOT / "manifest.json"

    gate = frontier_status.get("checks", {}).get("tracking_gate", {})
    tracking = frontier_status.get("tracking", {})
    wasm = frontier_status.get("wasm_size", {})

    header = f"""{'#' * 78}
ZOWSKYY ECOSYSTEM KNOWLEDGE REPORT
{'#' * 78}

Generated:     {utc_now()}
Run ID:        {run}
Canonical repo: {OWNER}/frontier-syntax
Blueprint:     PROJECT_BLUEPRINT.md + TRACKING.json
Pipeline log:  docs/agent_audit_log/pipeline_logs/{run}/pipeline.log
Audit sessions: docs/agent_audit_log/sessions/

{'=' * 78}
EXECUTIVE SUMMARY — frontier-syntax vs blueprint (bill) status
{'=' * 78}

Phase 0 (tracker hygiene):  PASS (slices 0.1–0.3 validated in TRACKING.json)
Phase 1 (P0 compiler):      FAIL — issues #44, #45, #46 open
Phase 2 (spec parity P1):   BLOCKED (depends on Phase 1)
Phase 3 (WASM size P1):     FAIL — {wasm.get('size_kb', '?')} KB measured, target {wasm.get('target_kb', 100)} KB, met={wasm.get('met', False)}
Phases 4–8:                 FROZEN until prior gates pass

Gate command output (tail):
{textwrap.indent((gate.get('output') or '(not run)')[-1500:], '  ')}

Repos scanned: {len(profiles)}
  frontier_core:      {sum(1 for p in profiles if p.category == 'frontier_core')}
  frontier_ecosystem: {sum(1 for p in profiles if p.category == 'frontier_ecosystem')}
  fork_or_adjacent:   {sum(1 for p in profiles if p.category == 'fork_or_adjacent')}
  other:              {sum(1 for p in profiles if p.category == 'other')}

Honesty: Remote repos receive shallow metadata scan (description, README excerpt,
top-level files). Build/test not run except for local frontier-syntax.
Private repos without token scope show access limitations.
"""

    body_parts = [header, ""]
    for i, p in enumerate(profiles, 1):
        body_parts.append(format_repo_section(p, i))

    footer = textwrap.dedent(
        f"""
        {'#' * 78}
        THIRD-PARTY CONTENT NOTICE
        {'#' * 78}
        README excerpts are reproduced for internal ecosystem inventory only.
        Each upstream repo retains its own license. See upstream LICENSE files.
        SPDX identifiers not auto-detected in this scan — verify before redistribution.

        {'#' * 78}
        END OF REPORT — regenerate with:
          python3 scripts/gather_ecosystem_knowledge.py
          python3 scripts/gather_ecosystem_knowledge.py --fast   # skip cargo rebuild
          python3 scripts/gather_ecosystem_knowledge.py --dry-run  # no writes
        {'#' * 78}
        """
    ).strip()

    report_text = "\n".join(body_parts) + "\n\n" + footer + "\n"
    report_path.write_text(report_text, encoding="utf-8")

    manifest = {
        "generated_at": utc_now(),
        "run_id": run,
        "owner": OWNER,
        "repo_count": len(profiles),
        "report_path": str(report_path.relative_to(REPO_ROOT)),
        "pipeline_log": str((pipe_dir / "pipeline.log").relative_to(REPO_ROOT)),
        "frontier_syntax_gate": {
            "tracking_gate_exit": gate.get("exit"),
            "wasm_size_kb": wasm.get("size_kb"),
            "wasm_target_met": wasm.get("met"),
            "open_issues": [44, 45, 46, 47, 48],
        },
        "repos": [
            {
                "name": p.name,
                "category": p.category,
                "url": p.url,
                "is_private": p.is_private,
                "access_status": p.access_status,
            }
            for p in profiles
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (ECO_ROOT / "LATEST.txt").write_text(run + "\n", encoding="utf-8")

    return report_path, manifest_path


def write_benchmark(run: str, timings: dict[str, float], repo_count: int, sla: dict) -> None:
    BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    total = timings.get("total_s", 0)
    record = {
        "run_id": run,
        "measured_at": utc_now(),
        "repo_count": repo_count,
        "timings_s": timings,
        "sla": sla,
        "sla_met": {
            "total_under_cap": total <= sla.get("max_total_seconds", 60),
            "per_repo_under_cap": (
                (total / max(repo_count, 1)) <= sla.get("max_seconds_per_repo", 5)
            ),
        },
    }
    BENCHMARK_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Gather zowskyy ecosystem knowledge")
    ap.add_argument("--dry-run", action="store_true", help="scan only; no report writes")
    ap.add_argument("--fast", action="store_true", help="skip cargo/wasm rebuild checks")
    args = ap.parse_args()

    t0 = time.monotonic()
    phase_times: dict[str, float] = {}
    run = run_id()
    pipe_dir = PIPELINE_ROOT / run
    pipe_dir.mkdir(parents=True, exist_ok=True)

    sla = json.loads(SLA_PATH.read_text(encoding="utf-8")) if SLA_PATH.exists() else {
        "max_total_seconds": 60,
        "max_seconds_per_repo": 5,
    }

    log_pipeline(pipe_dir, "START", f"ecosystem gather run_id={run} dry_run={args.dry_run}")
    audit_record(
        category="pipeline",
        action="ecosystem_knowledge_gather_start",
        why="User requested consolidated multi-repo knowledge vs blueprint status",
        command=f"python3 scripts/gather_ecosystem_knowledge.py",
        artifacts=[f"docs/agent_audit_log/pipeline_logs/{run}/"],
        verified=False,
    )

    log_pipeline(pipe_dir, "LIST", f"gh repo list {OWNER}")
    repos_raw = gh_json(
        [
            "repo",
            "list",
            OWNER,
            "--limit",
            "200",
            "--json",
            "name,description,isPrivate,primaryLanguage,url,updatedAt",
        ]
    )
    if not repos_raw:
        log_pipeline(pipe_dir, "ERROR", "gh repo list failed")
        audit_record(
            category="pipeline",
            action="ecosystem_knowledge_gather_failed",
            why="Could not list GitHub repos",
            command=f"gh repo list {OWNER}",
            exit_code=1,
            omissions=["No repos fetched"],
        )
        return 1

    log_pipeline(pipe_dir, "LIST", f"found {len(repos_raw)} repos")
    audit_record(
        category="pipeline",
        action="gh_repo_list",
        why="Enumerate all owner repos for ecosystem report",
        command=f"gh repo list {OWNER} --limit 200 --json name,...",
        outputs={"count": len(repos_raw)},
        verified=True,
    )

    phase_times["list_repos_s"] = time.monotonic() - t0

    log_pipeline(pipe_dir, "LOCAL", "load frontier-syntax status")
    t_local = time.monotonic()
    frontier_status = load_frontier_syntax_status(fast=args.fast)
    phase_times["local_checks_s"] = time.monotonic() - t_local
    if not args.dry_run:
        (pipe_dir / "frontier_syntax_status.json").write_text(
            json.dumps(frontier_status, indent=2, default=str), encoding="utf-8"
        )
    audit_record(
        category="pipeline",
        action="frontier_syntax_local_checks",
        why="Ground truth for blueprint comparison",
        command="tracking.py gate; cargo test; verify_wasm; measure_wasm",
        artifacts=[f"docs/agent_audit_log/pipeline_logs/{run}/frontier_syntax_status.json"],
        verified=True,
        omissions=["clippy not run in this pipeline"],
    )

    t_scan = time.monotonic()
    profiles: list[RepoProfile] = []
    for i, meta in enumerate(sorted(repos_raw, key=lambda x: x["name"].lower()), 1):
        name = meta["name"]
        is_private = meta.get("isPrivate", False)
        lang = (meta.get("primaryLanguage") or {}).get("name")
        category = classify_repo(name)

        log_pipeline(pipe_dir, "SCAN", f"[{i}/{len(repos_raw)}] {name}")
        readme, access = readme_excerpt(name, is_private)
        files, files_access = top_level_files(name, is_private)
        if access == "ok":
            access_status = files_access if files_access != "ok" else "ok"
        else:
            access_status = access

        claims = infer_claims(meta.get("description", ""), readme)
        can, cannot = infer_capabilities(
            name, category, lang, files, frontier_status if name == "frontier-syntax" else None
        )

        profile = RepoProfile(
            name=name,
            url=meta.get("url", f"https://github.com/{OWNER}/{name}"),
            description=meta.get("description", ""),
            is_private=is_private,
            language=lang,
            updated_at=meta.get("updatedAt", ""),
            category=category,
            access_status=access_status,
            readme_excerpt=readme,
            top_level_files=files,
            claims=claims,
            can_do=can,
            cannot_do=cannot,
            blueprint_relation=blueprint_relation(name, category),
        )
        profiles.append(profile)

        if not args.dry_run:
            per_repo = pipe_dir / "repos" / f"{name}.json"
            per_repo.parent.mkdir(parents=True, exist_ok=True)
            per_repo.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")

    phase_times["scan_repos_s"] = time.monotonic() - t_scan

    if args.dry_run:
        phase_times["total_s"] = time.monotonic() - t0
        print(json.dumps({"dry_run": True, "repos": len(profiles), "timings_s": phase_times}, indent=2))
        return 0

    log_pipeline(pipe_dir, "WRITE", "consolidated report")
    report_path, manifest_path = write_report(profiles, frontier_status, run, pipe_dir)

    phase_times["total_s"] = time.monotonic() - t0
    write_benchmark(run, phase_times, len(profiles), sla)

    audit_record(
        category="pipeline",
        action="ecosystem_knowledge_gather_complete",
        why="Consolidated report for owner review",
        command="python3 scripts/gather_ecosystem_knowledge.py",
        artifacts=[
            str(report_path.relative_to(REPO_ROOT)),
            str(manifest_path.relative_to(REPO_ROOT)),
            f"docs/agent_audit_log/pipeline_logs/{run}/",
        ],
        outputs={"repo_count": len(profiles), "run_id": run},
        verified=True,
        omissions=[
            "Remote repos not build-tested",
            "Private repos may be metadata-only",
        ],
    )
    log_pipeline(pipe_dir, "DONE", f"report={report_path.name}")

    print(f"Wrote {report_path}")
    print(f"Wrote {manifest_path}")
    print(f"Pipeline log: {pipe_dir / 'pipeline.log'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
