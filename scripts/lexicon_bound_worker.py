#!/usr/bin/env python3
"""
Lexicon-Bound Worker — every action documented, tagged, and woven into the Lexicon.

Python wrapper for Frontier lexicon-bound workers. All swarm actions flow through
execute_with_lexicon() so no action occurs without a permanent Lexicon trace.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
LEXICON_LOG = ROOT / "docs" / "lexicon_log.fr"
TICKETS_FILE = ROOT / "manifest" / "lexicon_user_tickets.json"
INDEX_FILE = ROOT / "manifest" / "lexicon_index.json"
_INDEX_LOCK = threading.Lock()
_CARGO_LOCK = threading.Lock()

HEADER = """// Frontier Lexicon — Living Knowledge Base
// Every action, every worker, every user is documented here
// ARC: Lexicon-Bound Worker — no action without Lexicon trace
version: 2.0;

module lexicon_log;

"""


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _sha3(data: str) -> str:
    return hashlib.sha3_256(data.encode("utf-8")).hexdigest()


class UserTicket:
    """User ticket bound to the Lexicon."""

    def __init__(self, user_id: str, lexicon: "LexiconBoundWorker"):
        self.ticket_id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = _sha3(f"{user_id}:{datetime.now(timezone.utc).isoformat()}")[:16]
        self.actions: list[str] = []
        self._lexicon = lexicon
        self._closed = False
        tag = lexicon.create_entry(
            user_id=user_id,
            action="ticket_creation",
            input_data={"user_id": user_id},
            output_data={"ticket_id": self.ticket_id},
            documentation="User ticket created for session",
            worker_id="system",
            parent_action=None,
        )
        self.actions.append(tag["action_id"])

    def add_action(self, action_id: str) -> None:
        self.actions.append(action_id)

    def close(self) -> dict:
        if self._closed:
            return {"ticket_id": self.ticket_id, "status": "already_closed"}
        tag = self._lexicon.create_entry(
            user_id=self.user_id,
            action="ticket_close",
            input_data={"ticket_id": self.ticket_id},
            output_data={"status": "closed", "action_count": len(self.actions)},
            documentation="User ticket closed",
            worker_id="system",
            parent_action=self.ticket_id,
        )
        self.actions.append(tag["action_id"])
        self._closed = True
        return {"ticket_id": self.ticket_id, "status": "closed", "lexicon_tag": tag["action_id"]}

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "user_id": _sha3(self.user_id),
            "session_id": self.session_id,
            "actions": self.actions,
            "closed": self._closed,
        }


class LexiconBoundWorker:
    """Worker that binds every action to the Lexicon."""

    def __init__(self, worker_id: str, user_id: str = "cloud_agent"):
        self.worker_id = worker_id
        self.user_id = user_id
        self.lexicon_file = LEXICON_LOG
        self._entries: list[dict] = []
        self._ensure_lexicon_file()
        self._load_index()

    def _ensure_lexicon_file(self) -> None:
        self.lexicon_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.lexicon_file.exists() or self.lexicon_file.stat().st_size == 0:
            self.lexicon_file.write_text(HEADER, encoding="utf-8")

    def _load_index(self) -> None:
        with _INDEX_LOCK:
            if INDEX_FILE.exists():
                try:
                    data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
                    self._entries = data.get("entries", [])
                except json.JSONDecodeError:
                    self._entries = []

    def _save_index(self) -> None:
        with _INDEX_LOCK:
            existing: dict[str, dict] = {}
            if INDEX_FILE.exists():
                try:
                    for e in json.loads(INDEX_FILE.read_text(encoding="utf-8")).get("entries", []):
                        if e.get("action_id"):
                            existing[e["action_id"]] = e
                except json.JSONDecodeError:
                    pass
            for e in self._entries:
                if e.get("action_id"):
                    existing[e["action_id"]] = e
            merged = list(existing.values())
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            INDEX_FILE.write_text(
                json.dumps({
                    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "entry_count": len(merged),
                    "entries": merged,
                }, indent=2),
                encoding="utf-8",
            )
            self._entries = merged

    def compute_delta(self, input_data: dict, output_data: dict) -> dict:
        inp = json.dumps(input_data, sort_keys=True, default=str)
        out = json.dumps(output_data, sort_keys=True, default=str)
        return {
            "input_keys": list(input_data.keys()) if isinstance(input_data, dict) else [],
            "output_keys": list(output_data.keys()) if isinstance(output_data, dict) else [],
            "changed": inp != out,
            "confidence": 0.95 if output_data.get("pass", output_data.get("status") == "executed") else 0.7,
        }

    def create_entry(
        self,
        user_id: str,
        action: str,
        input_data: dict,
        output_data: dict,
        documentation: str,
        worker_id: Optional[str] = None,
        parent_action: Optional[str] = None,
    ) -> dict:
        action_id = str(uuid.uuid4())
        user_hash = _sha3(user_id)
        inp_s = json.dumps(input_data, sort_keys=True, default=str)
        out_s = json.dumps(output_data, sort_keys=True, default=str)
        input_hash = _sha3(inp_s)
        output_hash = _sha3(out_s)
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lexicon_entry = _sha3(input_hash + output_hash)
        delta = self.compute_delta(input_data, output_data)

        entry = {
            "action_id": action_id,
            "user_id": user_hash,
            "worker_id": worker_id or self.worker_id,
            "timestamp": ts,
            "action_type": action,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "lexicon_entry": lexicon_entry,
            "parent_action": parent_action or "",
            "documentation": documentation,
            "knowledge_delta": delta,
        }
        self._log_to_lexicon(entry)
        self._entries.append(entry)
        self._save_index()
        return entry

    def _log_to_lexicon(self, entry: dict) -> None:
        safe_id = entry["action_id"].replace("-", "_")
        delta_json = _escape(json.dumps(entry["knowledge_delta"], separators=(",", ":")))
        block = f"""
component LexiconEntry_{safe_id} {{
    action_id: "{entry['action_id']}",
    user_id: "{entry['user_id']}",
    worker_id: "{entry['worker_id']}",
    timestamp: "{entry['timestamp']}",
    action_type: "{_escape(entry['action_type'])}",
    input_hash: "{entry['input_hash']}",
    output_hash: "{entry['output_hash']}",
    lexicon_entry: "{entry['lexicon_entry']}",
    parent_action: "{entry['parent_action']}",
    documentation: "{_escape(entry['documentation'])}",
    knowledge_delta: "{delta_json}",
}}
"""
        with open(self.lexicon_file, "a", encoding="utf-8") as f:
            f.write(block)

    def execute_with_lexicon(
        self,
        action: str,
        input_data: dict,
        documentation: str,
        executor: Callable[[], dict],
        user_id: Optional[str] = None,
        parent_action: Optional[str] = None,
    ) -> dict:
        uid = user_id or self.user_id
        tag = self.create_entry(
            user_id=uid,
            action=action,
            input_data=input_data,
            output_data={"status": "pending"},
            documentation=documentation,
            parent_action=parent_action,
        )
        try:
            output_data = executor()
        except Exception as exc:  # noqa: BLE001
            output_data = {"pass": False, "error": str(exc)}
        # Update with real output
        tag["output_hash"] = _sha3(json.dumps(output_data, sort_keys=True, default=str))
        tag["knowledge_delta"] = self.compute_delta(input_data, output_data)
        for i, e in enumerate(self._entries):
            if e["action_id"] == tag["action_id"]:
                self._entries[i] = {**e, **tag}
                break
        self._save_index()
        return {
            "output": output_data,
            "lexicon_tag": tag["action_id"],
            "documentation": documentation,
            "pass": output_data.get("pass", output_data.get("status") in ("executed", "success", "closed")),
        }

    def execute_command(
        self,
        action: str,
        cmd: list[str],
        documentation: str,
        user_id: Optional[str] = None,
    ) -> dict:
        def run() -> dict:
            import time
            start = time.perf_counter()
            if cmd and cmd[0] == "cargo":
                with _CARGO_LOCK:
                    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            else:
                r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            return {
                "pass": r.returncode == 0,
                "duration_ms": int((time.perf_counter() - start) * 1000),
                "output": (r.stdout + r.stderr)[-400:],
            }

        return self.execute_with_lexicon(
            action=action,
            input_data={"command": " ".join(cmd)},
            documentation=documentation,
            executor=run,
            user_id=user_id,
        )

    def query(self, term: str) -> list[dict]:
        term_lower = term.lower()
        return [
            e for e in self._entries
            if term_lower in e.get("action_type", "").lower()
            or term_lower in e.get("documentation", "").lower()
            or term_lower in e.get("worker_id", "").lower()
        ]

    def get_entry(self, action_id: str) -> Optional[dict]:
        for e in self._entries:
            if e["action_id"] == action_id:
                return e
        return None

    @classmethod
    def create_user_ticket(cls, user_id: str) -> UserTicket:
        worker = cls(worker_id="ticket_system", user_id=user_id)
        return UserTicket(user_id, worker)


def save_tickets(tickets: list[UserTicket]) -> None:
    TICKETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TICKETS_FILE.write_text(
        json.dumps([t.to_dict() for t in tickets], indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    w = LexiconBoundWorker("demo_worker")
    ticket = LexiconBoundWorker.create_user_ticket("demo_user")
    result = w.execute_command(
        "demo_action",
        ["python3", "-c", "print('lexicon-bound')"],
        "Demo lexicon-bound action",
        user_id="demo_user",
    )
    ticket.add_action(result["lexicon_tag"])
    ticket.close()
    save_tickets([ticket])
    print(json.dumps(result, indent=2))
