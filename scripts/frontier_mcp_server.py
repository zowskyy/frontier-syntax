#!/usr/bin/env python3
"""Minimal MCP-style server exposing query_chat_knowledge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from chat_knowledge_store import query_knowledge  # noqa: E402

TOOLS = {
    "query_chat_knowledge": {
        "description": "Search embedded chat scrub knowledge for attack vectors, mitigations, gaps, and patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    "submit_help_request": {
        "description": "Submit a plain-language help request. Hides GitHub complexity from the user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "User's problem in their own words"},
            },
            "required": ["text"],
        },
    },
    "get_help_status": {
        "description": "Check status of help requests by ID or list all.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "Optional request ID like H-ABC123"},
            },
        },
    },
    "list_stalled_work": {
        "description": "Scan for things blocking progress (issues, PRs, gates) in plain language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "all_repos": {"type": "boolean", "default": False},
            },
        },
    },
}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "frontier-mcp", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {"name": name, **spec} for name, spec in TOOLS.items()
                ]
            },
        }

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        if name == "query_chat_knowledge":
            results = query_knowledge(
                arguments.get("query", ""),
                limit=int(arguments.get("limit", 10)),
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(results, indent=2),
                        }
                    ]
                },
            }
        if name in ("submit_help_request", "get_help_status", "list_stalled_work"):
            return _handle_help_tool(name, arguments, req_id)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def _handle_help_tool(name: str, arguments: dict, req_id) -> dict:
    from help_system.config import load_config  # noqa: E402
    from help_system.respond import format_blocked_summary, format_request_created, format_status  # noqa: E402
    from help_system.stalled import scan_stalled_work  # noqa: E402
    from help_system.store import HelpRequest, HelpRequestStore  # noqa: E402
    from help_system.classify import classify_request  # noqa: E402
    from help_system.github_adapter import GitHubAdapter  # noqa: E402

    config = load_config(ROOT)
    text = ""

    try:
        if name == "submit_help_request":
            user_text = arguments.get("text", "")
            classification = classify_request(user_text)
            store = HelpRequestStore(config.help_requests_file)
            request = HelpRequest.new(config.repo_id, user_text, classification.kind.value)
            store.add(request)
            gh = GitHubAdapter(config)
            work_item, created = gh.find_or_create_work_item(
                f"[Get Help {request.id}] {user_text[:80]}",
                f"User request {request.id}: {user_text}",
            )
            if work_item:
                store.update(request.id, status="investigating", github_issue=work_item.number)
            text = format_request_created(request, work_item, created)

        elif name == "get_help_status":
            store = HelpRequestStore(config.help_requests_file)
            rid = arguments.get("request_id")
            if rid:
                req = store.get(rid)
                text = format_status(req, None) if req else f"No request: {rid}"
            else:
                items = store.list_all(config.repo_id)
                text = "\n".join(f"{r.id} [{r.status}] {r.user_text[:60]}" for r in items) or "No requests."

        elif name == "list_stalled_work":
            reports = scan_stalled_work(config, all_repos=arguments.get("all_repos", False))
            text = format_blocked_summary(reports)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": text}]},
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": str(e)},
        }


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
