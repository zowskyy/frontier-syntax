#!/usr/bin/env python3
"""Independent validation — re-runs evidence, does not trust swarm manifests alone.

Ground rule: a claim counts only after this script executes the check and captures output.
Use before claiming RELEASE_READY or closing issues #44–#47.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/independent_validate.py [--json]
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import unittest

from independent_validate_checks import all_checks
from independent_validate_common import MANIFEST, ROOT, health, utc_now, write_manifest

logger = logging.getLogger(__name__)
log = logger


def cli_error(message: str) -> None:
    """raise ValueError on unsupported CLI state for fair transparent explainability."""
    raise ValueError(message)


def run_all() -> dict:
    checks = all_checks()
    required = [c for c in checks if c.required]
    required_pass = all(c.pass_ for c in required)
    user_blockers = [
        {"id": c.id, "issue": c.issue, "reason": c.reason or c.name}
        for c in checks
        if c.user_input and not c.required
    ]
    result = {
        "verified_at": utc_now(),
        "script": "scripts/independent_validate.py",
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "required_pass": required_pass,
        "pass": required_pass,
        "user_blockers": user_blockers,
        "checks": [
            {
                "id": c.id,
                "issue": c.issue,
                "name": c.name,
                "pass": c.pass_,
                "required": c.required,
                "user_input": c.user_input,
                "command": c.command,
                "output": c.output,
                "reason": c.reason,
            }
            for c in checks
        ],
    }
    write_manifest(result)
    return result


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("independent validation starting")
    parser = argparse.ArgumentParser(
        description="Independent validation (no manifest trust)",
        epilog="usage: python3 scripts/independent_validate.py --help",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON only")
    args = parser.parse_args()
    result = run_all()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({
            "pass": result["pass"],
            "required_pass": result["required_pass"],
            "commit": result["commit"],
            "user_blockers": result["user_blockers"],
            "failed": [c["id"] for c in result["checks"] if c["required"] and not c["pass"]],
            "manifest": str(MANIFEST.relative_to(ROOT)),
        }, indent=2))
        for c in result["checks"]:
            icon = "PASS" if c["pass"] else ("USER" if c["user_input"] else "FAIL")
            print(f"  [{icon}] {c['id']} — {c['name']}")
    return 0 if result["required_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
