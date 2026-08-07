"""Detect stalled work — issues, PRs, gate failures."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import HelpConfig, load_global_registry
from .github_adapter import GitHubAdapter, WorkItem
from .store import HelpRequestStore


@dataclass
class StalledItem:
    repo_id: str
    category: str  # open_request | github_issue | github_pr | gate_failure | duplicate_issues
    title: str
    detail: str
    severity: str  # low | medium | high
    action: str


@dataclass
class StalledReport:
    repo_id: str
    items: list[StalledItem] = field(default_factory=list)
    scanned_at: str = ""

    @property
    def has_blockers(self) -> bool:
        return len(self.items) > 0


def scan_stalled_work(config: HelpConfig | None = None, all_repos: bool = False) -> list[StalledReport]:
    if all_repos:
        registry = load_global_registry()
        reports = []
        for entry in registry.get("repos", []):
            path = Path(entry.get("path", ""))
            if path.exists():
                cfg = __import__("help_system.config", fromlist=["load_config"]).load_config(path)
                reports.append(_scan_single_repo(cfg))
        if not reports:
            cfg = config or __import__("help_system.config", fromlist=["load_config"]).load_config()
            reports.append(_scan_single_repo(cfg))
        return reports

    cfg = config or __import__("help_system.config", fromlist=["load_config"]).load_config()
    return [_scan_single_repo(cfg)]


def _scan_single_repo(config: HelpConfig) -> StalledReport:
    report = StalledReport(
        repo_id=config.repo_id,
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )

    store = HelpRequestStore(config.help_requests_file)
    for req in store.list_open(config.repo_id):
        report.items.append(
            StalledItem(
                repo_id=config.repo_id,
                category="open_request",
                title=f"Your request {req.id} is open",
                detail=req.user_text[:100],
                severity="medium",
                action="An agent should pick this up or you can add more detail.",
            )
        )

    gh = GitHubAdapter(config)
    if gh.available:
        issues = gh.list_open_issues()
        prs = gh.list_open_prs()

        if len(issues) > 8:
            report.items.append(
                StalledItem(
                    repo_id=config.repo_id,
                    category="duplicate_issues",
                    title=f"{len(issues)} open tracked items (may include duplicates)",
                    detail="Too many open items slows progress.",
                    severity="high",
                    action="Run: python3 scripts/dedupe_issues.py (if this repo uses canonical issues)",
                )
            )

        for pr in prs[:5]:
            report.items.append(
                StalledItem(
                    repo_id=config.repo_id,
                    category="github_pr",
                    title=f"Change waiting to land: {pr.title}",
                    detail=pr.url,
                    severity="medium",
                    action="Review or merge when ready — you don't need to understand PR mechanics.",
                )
            )

        for issue in issues[:5]:
            if "get-help" in issue.labels or issue.number >= 40:
                report.items.append(
                    StalledItem(
                        repo_id=config.repo_id,
                        category="github_issue",
                        title=f"Known improvement in progress: {issue.title}",
                        detail=issue.url,
                        severity="low",
                        action="No action needed from you — work is tracked.",
                    )
                )

    gate = _check_tracking_gate(config)
    if gate:
        report.items.append(gate)

    return report


def _check_tracking_gate(config: HelpConfig) -> StalledItem | None:
    gate_script = config.repo_root / "scripts" / "tracking.py"
    if not gate_script.exists():
        return None
    r = subprocess.run(
        ["python3", str(gate_script), "gate"],
        cwd=config.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode == 0:
        return None
    return StalledItem(
        repo_id=config.repo_id,
        category="gate_failure",
        title="Validation gate has not passed yet",
        detail=(r.stdout + r.stderr)[-200:],
        severity="high",
        action="Automated checks must pass before work can be marked complete.",
    )
