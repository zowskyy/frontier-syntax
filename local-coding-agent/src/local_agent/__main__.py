# SPDX-License-Identifier: Apache-2.0
"""CLI entrypoint: agent benchmark, release validate."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from local_agent.benchmark.harness import BenchmarkHarness
from local_agent.mobile import MobileCore, MobileSecurity
from local_agent.release import ReleaseEngineering

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local coding agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("benchmark", help="Run reproducible benchmark harness")
    bench.add_argument("--profile", choices=["desktop", "android", "ios"], default="desktop")

    sub.add_parser("release-validate", help="Run release candidate validation (SLICE 35)")
    sub.add_parser("mobile-check", help="Write mobile security evidence scaffolds")

    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent.parent

    if args.command == "benchmark":
        report = BenchmarkHarness(root, profile=args.profile).run()
        print(json.dumps({"profile": report.profile, "summary": report.summary}, indent=2))
        return 0

    if args.command == "release-validate":
        rc = ReleaseEngineering(root).validate_rc()
        print(json.dumps(rc, indent=2))
        return 0 if rc.get("go_decision_allowed") else 1

    if args.command == "mobile-check":
        sec = MobileSecurity()
        for platform in ("android", "ios"):
            path = sec.write_evidence(root.parent / "evidence" / "mobile" / platform, platform)
            core = MobileCore().profile(platform)
            log.info("%s path=%s inference=%s", platform, path, core.inference_path)
        return 0

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
