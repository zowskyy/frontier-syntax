#!/usr/bin/env python3
"""Phase 8 launch gate — external launch checklist + manifest evidence."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "launch_status.json"
CHECKLIST = ROOT / "LAUNCH_CHECKLIST.md"
OUT = ROOT / "manifest" / "phase8_launch_verify.json"

REQUIRED_LAUNCH_FIELDS = (
    "discord_url",
    "website_url",
    "social_urls",
    "waitlist_url",
    "launch_date",
)


def checklist_complete() -> tuple[bool, list[str]]:
    if not CHECKLIST.exists():
        return False, ["LAUNCH_CHECKLIST.md missing"]
    text = CHECKLIST.read_text(encoding="utf-8")
    pending = []
    for item in ("Discord server", "Website live", "Social media", "Waiting list", "Launch date"):
        if f"- [ ] {item}" in text:
            pending.append(item)
    return len(pending) == 0, pending


def load_launch_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def url_reachable(url: str, timeout: int = 8) -> bool:
    if not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 303, 307, 308)
    except Exception:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status in (200, 301, 302)
        except Exception:
            return False


def verify(*, check_urls: bool = True) -> dict:
    manifest = load_launch_manifest()
    missing_fields = [f for f in REQUIRED_LAUNCH_FIELDS if not manifest.get(f)]
    checklist_ok, pending = checklist_complete()

    url_checks: dict[str, bool] = {}
    if check_urls and manifest.get("website_url"):
        url_checks["website_url"] = url_reachable(str(manifest["website_url"]))

    social = manifest.get("social_urls") or []
    if check_urls and social:
        url_checks["social_urls"] = all(url_reachable(u) for u in social[:3])

    ok = (
        not missing_fields
        and checklist_ok
        and (not check_urls or url_checks.get("website_url", True))
    )

    result = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_phase8_launch.py",
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "checklist_ok": checklist_ok,
        "pending_checklist_items": pending,
        "missing_manifest_fields": missing_fields,
        "url_checks": url_checks,
        "pass": ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify Phase 8 launch readiness")
    parser.add_argument("--skip-url-check", action="store_true")
    args = parser.parse_args()
    result = verify(check_urls=not args.skip_url_check)
    print(json.dumps(result, indent=2))
    if result["pass"]:
        print("PASS: Phase 8 launch gate")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
