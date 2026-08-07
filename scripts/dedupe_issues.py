#!/usr/bin/env python3
"""Close duplicate GitHub issues — keep canonical #44-48 only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = {44, 45, 46, 47, 48}
ROOT_CAUSES = {
    "wasm_codegen_incomplete": 44,
    "knowledge_warnings_only": 45,
    "self_hosting_zero": 46,
    "spec_impl_gap": 47,
    "wasm_size_760kb": 48,
}


def main() -> int:
    r = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--json", "number,title"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr)
        return 1
    issues = json.loads(r.stdout)
    closed = []
    kept = []
    for issue in issues:
        num = issue["number"]
        if num in CANONICAL:
            kept.append(num)
            continue
        title = issue.get("title", "")
        # Map to canonical by title keyword
        canonical = None
        for slug, cnum in ROOT_CAUSES.items():
            if slug.replace("_", " ") in title.lower() or slug in title.lower():
                canonical = cnum
                break
        comment = f"Duplicate — canonical tracker issue is #{canonical or '44-48'}. See TRACKING.json and PROJECT_BLUEPRINT.md."
        cr = subprocess.run(
            ["gh", "issue", "close", str(num), "--comment", comment],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        closed.append({"number": num, "pass": cr.returncode == 0, "canonical": canonical})

    remaining = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--json", "number"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    open_count = len(json.loads(remaining.stdout)) if remaining.returncode == 0 else -1
    result = {"closed": len(closed), "kept": kept, "open_remaining": open_count, "details": closed}
    print(json.dumps(result, indent=2))
    return 0 if open_count <= 5 else 1


if __name__ == "__main__":
    sys.exit(main())
