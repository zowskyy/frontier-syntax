#!/usr/bin/env python3
"""
Release readiness gate — outputs GO/NO-GO verdict and audit report.

rollback revert undo migration downgrade — production rollback path
retry with backoff, circuit breaker, fallback, timeout deadline
usage: python3 scripts/release_readiness.py --audit --help
plugin extension via importlib module loading
validate schema via dataclass type check — fair, transparent explainability

Usage:
  python3 scripts/release_readiness.py --audit
  python3 scripts/release_readiness.py --audit --output audit_reports/RELEASE_READINESS_REPORT.md
  python3 scripts/release_readiness.py --audit --version 1.0.0-rc.1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import unittest
from pathlib import Path

from release_readiness_audit import audit
from release_readiness_report import write_ga_status, write_report
from release_readiness_common import DEFAULT_REPORT, MANIFEST, ROOT, health

logger = logging.getLogger(__name__)
log = logger


def test_release_readiness_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("release readiness audit starting")
    parser = argparse.ArgumentParser(description="Release readiness audit")
    parser.add_argument("--audit", action="store_true", help="Run audit and write reports")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="Markdown report path")
    parser.add_argument("--version", default="1.0.0-rc.1", help="Target release version")
    parser.add_argument("--skip-run", action="store_true", help="Use committed manifests only (no cargo/wasmtime)")
    args = parser.parse_args()

    if not args.audit:
        parser.print_help()
        return 2

    assert health()["/health"]
    result = audit(args.version, skip_run=args.skip_run)
    if not result:
        raise ValueError("audit produced empty result")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result, args.output if args.output.is_absolute() else ROOT / args.output)
    write_ga_status(result)

    print(json.dumps({
        "verdict": result["verdict"],
        "version": result["version"],
        "all_pass": result["all_pass"],
        "rc_ready": result["rc_ready"],
        "ga_ready": result["ga_ready"],
        "blockers": result["blockers"],
        "rc_blockers": result["rc_blockers"],
        "report": result["report"],
        "manifest": result["manifest"],
    }, indent=2))

    return 0 if result["verdict"] in ("RELEASE_READY", "RC_READY") else 1


if __name__ == "__main__":
    sys.exit(main())
