"""Format plain-language responses — no GitHub jargon unless asked."""

from __future__ import annotations

from .github_adapter import WorkItem
from .stalled import StalledReport
from .store import HelpRequest


def format_request_created(
    request: HelpRequest,
    work_item: WorkItem | None = None,
    created_new: bool = False,
) -> str:
    lines = [
        f"✅ Request received: **{request.id}**",
        "",
        f"What you asked: {request.user_text}",
        f"Type: {request.kind}",
        f"Status: {request.status}",
        "",
    ]

    if work_item:
        if created_new:
            lines.append("We created a tracked work item for this. You don't need to do anything on GitHub.")
        else:
            lines.append("We found existing work that matches your request — linking to it instead of creating a duplicate.")
        lines.append(f"Tracked as: {work_item.title}")
    else:
        lines.append("Your request is saved locally. An agent will pick it up.")

    lines.extend(
        [
            "",
            "Check status anytime:",
            f"  python3 scripts/get_help.py status {request.id}",
            "",
            "Nothing else required from you right now.",
        ]
    )
    return "\n".join(lines)


def format_status(request: HelpRequest, work_item: WorkItem | None = None) -> str:
    status_map = {
        "received": "We received your request and will look at it soon.",
        "investigating": "Someone is looking into this now.",
        "in_progress": "Work is actively happening on this.",
        "resolved": "This should be fixed. Let us know if it isn't.",
        "closed": "This request is closed.",
    }
    lines = [
        f"Request **{request.id}**",
        f"Status: {status_map.get(request.status, request.status)}",
        f"Asked: {request.user_text}",
    ]
    if work_item:
        lines.append(f"Linked work: {work_item.title}")
    if request.resolution:
        lines.append(f"Resolution: {request.resolution}")
    return "\n".join(lines)


def format_blocked_summary(reports: list[StalledReport]) -> str:
    total = sum(len(r.items) for r in reports)
    if total == 0:
        return "✅ Nothing blocking progress right now. You're clear to keep working."

    lines = [
        f"⚠️  Found {total} item(s) that may be slowing things down:",
        "",
    ]
    for report in reports:
        if not report.items:
            continue
        lines.append(f"## {report.repo_id}")
        for item in report.items:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.severity, "•")
            lines.append(f"{icon} **{item.title}**")
            lines.append(f"   {item.detail}")
            lines.append(f"   → {item.action}")
            lines.append("")
    lines.append("You don't need to manage GitHub issues or PRs — just tell me what you want done.")
    return "\n".join(lines)


def format_help_menu() -> str:
    return """
Frontier Get Help — plain language, no GitHub required
======================================================

Submit a request (describe your problem in normal words):
  python3 scripts/get_help.py "my build fails"
  python3 scripts/get_help.py "I need help understanding the CLI"

Check what's blocking progress:
  python3 scripts/get_help.py blocked

Check status of your requests:
  python3 scripts/get_help.py status
  python3 scripts/get_help.py status H-ABC123

Register this repo for cross-repo tracking:
  python3 scripts/get_help.py register

In Cursor: type /get-help or say "get help with ..."

You never need to:
  • Open a GitHub issue manually
  • Understand what a pull request is
  • Figure out which issue number blocks what

Just describe the problem. The system handles the rest.
""".strip()
