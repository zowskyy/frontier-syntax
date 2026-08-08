#!/usr/bin/env python3
"""Example echo plugin — JSON-RPC over stdin/stdout."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def get_permissions() -> list[str]:
    raw = os.environ.get("PLUGIN_PERMISSIONS", "[]")
    return json.loads(raw)


def handle_request(req: dict[str, Any]) -> dict[str, Any]:
    method = req.get("method", "")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "health":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"status": "ok"}}

    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"status": "shutting_down"}}

    if method == "echo":
        perms = get_permissions()
        if "echo" not in perms:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": "Permission denied: echo"},
            }
        message = params.get("message", "")
        return {"jsonrpc": "2.0", "id": req_id, "result": {"echo": message}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        resp = handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
        if req.get("method") == "shutdown":
            break


if __name__ == "__main__":
    main()
