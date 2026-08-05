#!/usr/bin/env python3
"""Install continuous scrub daemon and git event hooks."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".git" / "hooks"
DAEMON_SCRIPT = ROOT / "scripts" / "scrub_daemon.py"


def write_daemon(interval: int) -> None:
    content = f'''#!/usr/bin/env python3
"""Continuous scrub daemon — runs delta scrub on interval."""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERVAL = {interval}

def main() -> None:
    while True:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "scrub_with_retry.py"), "--delta"],
            cwd=ROOT,
        )
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
'''
    DAEMON_SCRIPT.write_text(content, encoding="utf-8")
    DAEMON_SCRIPT.chmod(DAEMON_SCRIPT.stat().st_mode | stat.S_IEXEC)


def write_post_merge_hook() -> None:
    hook = HOOKS_DIR / "post-merge"
    snippet = '''
# frontier-scrub: delta scrub after merge
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/scrub_with_retry.py --delta >/dev/null 2>&1 &
fi
'''
    existing = hook.read_text(encoding="utf-8") if hook.exists() else "#!/bin/sh\n"
    if "frontier-scrub" not in existing:
        hook.write_text(existing.rstrip() + "\n" + snippet, encoding="utf-8")
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC)


def write_post_commit_hook(branch: str) -> None:
    hook = HOOKS_DIR / "post-commit"
    snippet = f'''
# frontier-scrub: delta scrub on base branch commits
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$BRANCH" = "{branch}" ] && command -v python3 >/dev/null 2>&1; then
  python3 scripts/scrub_with_retry.py --delta >/dev/null 2>&1 &
fi
'''
    existing = hook.read_text(encoding="utf-8") if hook.exists() else "#!/bin/sh\n"
    if "frontier-scrub" not in existing:
        hook.write_text(existing.rstrip() + "\n" + snippet, encoding="utf-8")
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install continuous scrub daemon")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between scrubs")
    parser.add_argument("--branch", default="cursor/frontier-syntax-cycle1-e39f")
    parser.add_argument("--hooks-only", action="store_true")
    args = parser.parse_args()

    if not (ROOT / ".git").exists():
        print("FAIL: not a git repository")
        return 1

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    write_daemon(args.interval)
    write_post_merge_hook()
    write_post_commit_hook(args.branch)

    print(f"✅ Daemon script: {DAEMON_SCRIPT.relative_to(ROOT)}")
    print(f"✅ Git hooks installed in {HOOKS_DIR.relative_to(ROOT)}")
    print(f"   Interval: {args.interval}s | Branch trigger: {args.branch}")
    if not args.hooks_only:
        print(f"   Start daemon: python3 {DAEMON_SCRIPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
