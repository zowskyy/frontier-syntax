#!/usr/bin/env python3
"""One-line hook to log ANY tool call — no significance filter."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOGGER = REPO / "scripts" / "agent_audit_logger.py"


def main() -> int:
    p = argparse.ArgumentParser(description="Log one tool invocation")
    p.add_argument("--tool", required=True, help="Tool name: Shell, Read, Grep, Write, etc.")
    p.add_argument("--action", required=True, help="What was done")
    p.add_argument("--why", default="User-directed work; log every action per owner policy")
    p.add_argument("--command", default="")
    p.add_argument("--path", default="")
    p.add_argument("--exit-code", type=int, default=None)
    p.add_argument("--verified", action="store_true")
    p.add_argument("--omission", action="append", default=[])
    args = p.parse_args()

    outputs = {}
    if args.exit_code is not None:
        outputs["exit_code"] = args.exit_code
    if args.path:
        outputs["path"] = args.path

    cmd = [
        sys.executable,
        str(LOGGER),
        "record",
        "--category",
        "tool_call",
        "--tool",
        args.tool,
        "--action",
        args.action,
        "--why",
        args.why,
        "--command",
        args.command or args.path,
        "--script",
        "scripts/agent_audit_hook.py",
        "--outputs",
        json.dumps(outputs),
    ]
    if args.verified:
        cmd.append("--verified")
    for o in args.omission:
        cmd.extend(["--omission", o])

    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
