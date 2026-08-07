#!/usr/bin/env python3
"""
Get Help — cross-repo plain-language help system.

You describe problems in normal words. GitHub issues/PRs are handled for you.

Usage:
  python3 scripts/get_help.py "my WASM compile fails"
  python3 scripts/get_help.py blocked
  python3 scripts/get_help.py status
  python3 scripts/get_help.py status H-ABC123
  python3 scripts/get_help.py register
  python3 scripts/get_help.py --all-repos blocked
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from help_system.classify import RequestKind, classify_request  # noqa: E402
from help_system.config import load_config, register_repo  # noqa: E402
from help_system.github_adapter import GitHubAdapter  # noqa: E402
from help_system.respond import (  # noqa: E402
    format_blocked_summary,
    format_help_menu,
    format_request_created,
    format_status,
)
from help_system.stalled import scan_stalled_work  # noqa: E402
from help_system.store import HelpRequest, HelpRequestStore  # noqa: E402


def try_knowledge_answer(text: str) -> str | None:
    try:
        from chat_knowledge_store import query_knowledge  # type: ignore

        results = query_knowledge(text, limit=3)
        if results:
            top = results[0]
            snippet = top.get("text", "")[:400]
            if snippet:
                return f"From project knowledge:\n{snippet}\n"
    except Exception:
        pass
    return None


def handle_submit(text: str, config) -> int:
    classification = classify_request(text)

    if classification.kind == RequestKind.STATUS:
        return handle_status(None, config)

    if classification.kind == RequestKind.BLOCKED:
        return handle_blocked(config, all_repos=False)

    store = HelpRequestStore(config.help_requests_file)
    request = HelpRequest.new(config.repo_id, text, classification.kind.value)
    store.add(request)

    # Try instant answer for questions
    if classification.kind == RequestKind.QUESTION:
        answer = try_knowledge_answer(text)
        if answer:
            store.update(request.id, status="resolved", resolution="Answered from knowledge base")
            print(answer)
            print(f"\n(Request {request.id} — answered immediately. Ask again if you need more.)")
            return 0

    gh = GitHubAdapter(config)
    work_item = None
    created = False
    if classification.kind in (RequestKind.BUG, RequestKind.STUCK, RequestKind.FEATURE, RequestKind.UNKNOWN):
        body = (
            f"**Get Help request:** {request.id}\n\n"
            f"**User said:** {text}\n\n"
            f"**Classification:** {classification.kind.value}\n\n"
            f"**Suggested action:** {classification.suggested_action}\n\n"
            f"---\n_Auto-created by Get Help system. User does not need to interact with GitHub._"
        )
        title = f"[Get Help {request.id}] {text[:80]}"
        work_item, created = gh.find_or_create_work_item(title, body)
        if work_item:
            store.update(
                request.id,
                status="investigating",
                github_issue=work_item.number if work_item.kind == "issue" else None,
            )

    print(format_request_created(request, work_item, created))
    return 0


def handle_status(request_id: str | None, config) -> int:
    store = HelpRequestStore(config.help_requests_file)
    gh = GitHubAdapter(config)

    if request_id:
        req = store.get(request_id)
        if not req:
            print(f"No request found for: {request_id}")
            return 1
        work_item = None
        if req.github_issue and gh.available:
            for issue in gh.list_open_issues():
                if issue.number == req.github_issue:
                    work_item = issue
                    break
        print(format_status(req, work_item))
        return 0

    requests = store.list_all(config.repo_id)
    if not requests:
        print("No requests yet. Submit one with:")
        print('  python3 scripts/get_help.py "describe your problem"')
        return 0

    print(f"Your requests in {config.repo_id}:\n")
    for req in requests[:10]:
        print(f"  {req.id}  [{req.status}]  {req.user_text[:60]}")
    print("\nDetails: python3 scripts/get_help.py status <ID>")
    return 0


def handle_blocked(config, all_repos: bool) -> int:
    reports = scan_stalled_work(config, all_repos=all_repos)
    print(format_blocked_summary(reports))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Get Help — plain language, GitHub handled for you")
    parser.add_argument("text", nargs="*", help="Describe your problem, or use subcommands")
    parser.add_argument("--all-repos", action="store_true", help="Scan all registered repos")
    args = parser.parse_args()

    config = load_config()

    if not args.text:
        print(format_help_menu())
        return 0

    command = args.text[0].lower()
    rest = " ".join(args.text[1:])

    if command in ("help", "--help", "-h"):
        print(format_help_menu())
        return 0

    if command == "blocked":
        return handle_blocked(config, all_repos=args.all_repos)

    if command == "status":
        return handle_status(rest.strip() or None, config)

    if command == "register":
        register_repo(config)
        print(f"✅ Registered {config.repo_id} at {config.repo_root}")
        print(f"   Global registry: ~/.frontier/help/repos.json")
        return 0

    if command == "menu":
        print(format_help_menu())
        return 0

    # Default: treat entire input as a help request
    full_text = " ".join(args.text)
    return handle_submit(full_text, config)


if __name__ == "__main__":
    sys.exit(main())
