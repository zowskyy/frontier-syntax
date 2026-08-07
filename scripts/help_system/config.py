"""Configuration for the cross-repo Get Help system."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GLOBAL_REGISTRY = Path.home() / ".frontier" / "help" / "repos.json"
GLOBAL_STATE_DIR = Path.home() / ".frontier" / "help"


@dataclass
class HelpConfig:
    repo_root: Path
    repo_id: str
    repo_name: str
    github_owner: str = ""
    github_repo: str = ""
    canonical_issue_labels: list[str] = field(default_factory=lambda: ["get-help"])
    auto_create_github: bool = True
    tracking_file: Path | None = None

    @property
    def manifest_dir(self) -> Path:
        return self.repo_root / "manifest"

    @property
    def help_requests_file(self) -> Path:
        return self.manifest_dir / "help_requests.jsonl"

    @property
    def local_config_file(self) -> Path:
        return self.manifest_dir / "help_config.json"


def _git_remote_info(repo_root: Path) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return "", ""
        url = result.stdout.strip()
        # https://github.com/owner/repo or git@github.com:owner/repo.git
        if "github.com" in url:
            parts = url.rstrip("/").rstrip(".git").split("/")
            if len(parts) >= 2:
                return parts[-2], parts[-1]
    except OSError:
        pass
    return "", ""


def load_config(start_dir: Path | None = None) -> HelpConfig:
    repo_root = find_repo_root(start_dir or Path.cwd())
    owner, repo = _git_remote_info(repo_root)
    repo_id = repo or repo_root.name
    local_file = repo_root / "manifest" / "help_config.json"
    data: dict[str, Any] = {}
    if local_file.exists():
        data = json.loads(local_file.read_text(encoding="utf-8"))

    tracking = data.get("tracking_file")
    tracking_path = (repo_root / tracking) if tracking else None
    if tracking_path and not tracking_path.exists():
        alt = repo_root / "TRACKING.json"
        tracking_path = alt if alt.exists() else None

    return HelpConfig(
        repo_root=repo_root,
        repo_id=data.get("repo_id", repo_id),
        repo_name=data.get("repo_name", repo or repo_root.name),
        github_owner=data.get("github_owner", owner),
        github_repo=data.get("github_repo", repo),
        canonical_issue_labels=data.get("labels", ["get-help"]),
        auto_create_github=data.get("auto_create_github", True),
        tracking_file=tracking_path,
    )


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return start.resolve()


def load_global_registry() -> dict[str, Any]:
    GLOBAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not GLOBAL_REGISTRY.exists():
        return {"repos": [], "version": "1.0.0"}
    return json.loads(GLOBAL_REGISTRY.read_text(encoding="utf-8"))


def register_repo(config: HelpConfig) -> None:
    registry = load_global_registry()
    entry = {
        "id": config.repo_id,
        "name": config.repo_name,
        "path": str(config.repo_root),
        "github": f"{config.github_owner}/{config.github_repo}"
        if config.github_owner and config.github_repo
        else "",
        "registered_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    repos = [r for r in registry.get("repos", []) if r.get("id") != config.repo_id]
    repos.append(entry)
    registry["repos"] = repos
    GLOBAL_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
