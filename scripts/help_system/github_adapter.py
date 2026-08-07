"""GitHub adapter — hide issues/PRs behind plain-language operations."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from .config import HelpConfig


@dataclass
class WorkItem:
    number: int
    title: str
    state: str
    url: str
    kind: str  # issue | pr
    labels: list[str]
    created_at: str = ""
    is_stale: bool = False


class GitHubAdapter:
    def __init__(self, config: HelpConfig) -> None:
        self.config = config
        self.available = self._gh_available()

    def _gh_available(self) -> bool:
        try:
            r = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return r.returncode == 0
        except OSError:
            return False

    def _run(self, args: list[str]) -> tuple[bool, str]:
        if not self.available:
            return False, "GitHub CLI not authenticated (run: gh auth login)"
        cmd = ["gh", *args]
        if self.config.github_owner and self.config.github_repo:
            cmd.extend(["--repo", f"{self.config.github_owner}/{self.config.github_repo}"])
        r = subprocess.run(cmd, cwd=self.config.repo_root, capture_output=True, text=True)
        output = (r.stdout + r.stderr).strip()
        return r.returncode == 0, output

    def find_similar_issues(self, query: str, limit: int = 5) -> list[WorkItem]:
        ok, out = self._run(
            ["issue", "list", "--state", "open", "--json", "number,title,url,labels,createdAt", "--limit", "30"]
        )
        if not ok:
            return []
        issues = json.loads(out) if out.startswith("[") else []
        keywords = set(re.findall(r"[a-z]{4,}", query.lower()))
        scored: list[tuple[int, WorkItem]] = []
        for issue in issues:
            title = issue.get("title", "").lower()
            overlap = sum(1 for k in keywords if k in title)
            if overlap > 0:
                labels = [lb.get("name", "") for lb in issue.get("labels", [])]
                scored.append(
                    (
                        overlap,
                        WorkItem(
                            number=issue["number"],
                            title=issue["title"],
                            state="open",
                            url=issue["url"],
                            kind="issue",
                            labels=labels,
                            created_at=issue.get("createdAt", ""),
                        ),
                    )
                )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def find_or_create_work_item(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> tuple[WorkItem | None, bool]:
        """Return (work_item, created). created=False means existing match."""
        labels = labels or self.config.canonical_issue_labels
        similar = self.find_similar_issues(title, limit=3)
        if similar:
            return similar[0], False

        if not self.config.auto_create_github:
            return None, False

        label_args: list[str] = []
        for label in labels:
            label_args.extend(["--label", label])

        ok, out = self._run(
            [
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                *label_args,
            ]
        )
        if not ok:
            return None, False

        # gh issue create outputs URL
        number_match = re.search(r"/issues/(\d+)", out)
        number = int(number_match.group(1)) if number_match else 0
        return (
            WorkItem(
                number=number,
                title=title,
                state="open",
                url=out.strip(),
                kind="issue",
                labels=labels,
            ),
            True,
        )

    def list_open_prs(self) -> list[WorkItem]:
        ok, out = self._run(
            ["pr", "list", "--state", "open", "--json", "number,title,url,createdAt,labels"]
        )
        if not ok:
            return []
        prs = json.loads(out) if out.startswith("[") else []
        return [
            WorkItem(
                number=pr["number"],
                title=pr["title"],
                state="open",
                url=pr["url"],
                kind="pr",
                labels=[lb.get("name", "") for lb in pr.get("labels", [])],
                created_at=pr.get("createdAt", ""),
            )
            for pr in prs
        ]

    def list_open_issues(self) -> list[WorkItem]:
        ok, out = self._run(
            ["issue", "list", "--state", "open", "--json", "number,title,url,createdAt,labels"]
        )
        if not ok:
            return []
        issues = json.loads(out) if out.startswith("[") else []
        return [
            WorkItem(
                number=issue["number"],
                title=issue["title"],
                state="open",
                url=issue["url"],
                kind="issue",
                labels=[lb.get("name", "") for lb in issue.get("labels", [])],
                created_at=issue.get("createdAt", ""),
            )
            for issue in issues
        ]

    def human_label(self, item: WorkItem) -> str:
        kind_word = "fix" if item.kind == "issue" else "change ready for review"
        return f"{item.title} ({kind_word})"
