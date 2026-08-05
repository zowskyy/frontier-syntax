#!/usr/bin/env python3
"""Self-healing wrapper for chat scrub with exponential backoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRUB_SCRIPT = ROOT / "scripts" / "generate_chat_scrub.py"
STATE_FILE = ROOT / ".frontier_scrub_state.json"
LOG_FILE = ROOT / "chat_scrub" / "scrub_retry.log"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"runs": [], "last_success": None, "failures": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def log_line(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")
    print(message)


def run_scrub(delta: bool = False) -> int:
    cmd = [sys.executable, str(SCRUB_SCRIPT)]
    if delta:
        cmd.append("--delta")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "scrub failed")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-healing chat scrub wrapper")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--base-delay", type=float, default=2.0)
    parser.add_argument("--delta", action="store_true", help="Delta extraction mode")
    args = parser.parse_args()

    state = load_state()
    attempt = 0

    while attempt < args.max_retries:
        attempt += 1
        try:
            log_line(f"Scrub attempt {attempt}/{args.max_retries}")
            run_scrub(delta=args.delta)
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            state["last_success"] = now
            state["failures"] = 0
            state["runs"].append({"at": now, "status": "success", "attempt": attempt})
            save_state(state)
            log_line("Scrub succeeded")
            return 0
        except Exception as exc:  # noqa: BLE001
            state["failures"] = state.get("failures", 0) + 1
            state["runs"].append(
                {
                    "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "status": "failed",
                    "attempt": attempt,
                    "error": str(exc),
                }
            )
            save_state(state)
            log_line(f"Scrub failed: {exc}")
            log_line(traceback.format_exc())
            if attempt >= args.max_retries:
                log_line("Max retries exceeded")
                return 1
            delay = args.base_delay * (2 ** (attempt - 1))
            log_line(f"Retrying in {delay:.1f}s")
            time.sleep(delay)

    return 1


if __name__ == "__main__":
    sys.exit(main())
