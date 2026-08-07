#!/usr/bin/env python3
"""Cross-repo Get Help system — plain language intake, GitHub complexity hidden."""

from help_system.classify import classify_request
from help_system.config import HelpConfig, load_config
from help_system.github_adapter import GitHubAdapter
from help_system.respond import format_blocked_summary, format_request_created, format_status
from help_system.stalled import scan_stalled_work
from help_system.store import HelpRequestStore

__all__ = [
    "HelpConfig",
    "load_config",
    "classify_request",
    "GitHubAdapter",
    "HelpRequestStore",
    "format_status",
    "format_request_created",
    "format_blocked_summary",
    "scan_stalled_work",
]

__version__ = "1.0.0"
