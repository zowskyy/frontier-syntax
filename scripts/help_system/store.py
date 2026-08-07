"""Persist help requests locally — user-facing IDs, not GitHub numbers."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HelpRequest:
    id: str
    repo_id: str
    user_text: str
    kind: str
    status: str  # received | investigating | in_progress | resolved | closed
    created_at: str
    updated_at: str
    github_issue: int | None = None
    github_pr: int | None = None
    notes: list[str] = field(default_factory=list)
    resolution: str = ""

    @staticmethod
    def new(repo_id: str, user_text: str, kind: str) -> "HelpRequest":
        now = datetime.now(timezone.utc).isoformat()
        short = uuid.uuid4().hex[:6].upper()
        return HelpRequest(
            id=f"H-{short}",
            repo_id=repo_id,
            user_text=user_text,
            kind=kind,
            status="received",
            created_at=now,
            updated_at=now,
        )


class HelpRequestStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> list[HelpRequest]:
        if not self.path.exists():
            return []
        requests: list[HelpRequest] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            requests.append(HelpRequest(**data))
        return requests

    def _write_all(self, requests: list[HelpRequest]) -> None:
        lines = [json.dumps(asdict(r), ensure_ascii=False) for r in requests]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def add(self, request: HelpRequest) -> HelpRequest:
        requests = self._read_all()
        requests.append(request)
        self._write_all(requests)
        return request

    def update(self, request_id: str, **fields: Any) -> HelpRequest | None:
        requests = self._read_all()
        for i, req in enumerate(requests):
            if req.id == request_id or req.id.endswith(request_id):
                data = asdict(req)
                data.update(fields)
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = HelpRequest(**data)
                requests[i] = updated
                self._write_all(requests)
                return updated
        return None

    def get(self, request_id: str) -> HelpRequest | None:
        for req in self._read_all():
            if req.id == request_id or req.id.endswith(request_id.upper()):
                return req
        return None

    def list_open(self, repo_id: str | None = None) -> list[HelpRequest]:
        open_statuses = {"received", "investigating", "in_progress"}
        return [
            r
            for r in self._read_all()
            if r.status in open_statuses
            and (repo_id is None or r.repo_id == repo_id)
        ]

    def list_all(self, repo_id: str | None = None, limit: int = 20) -> list[HelpRequest]:
        items = self._read_all()
        if repo_id:
            items = [r for r in items if r.repo_id == repo_id]
        return list(reversed(items[-limit:]))
