#!/usr/bin/env python3
"""On-demand fetch bridge — live URL fetch without cache."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


def fetch_live(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Frontier-OnDemandFetcher/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read(64_000)
        return {
            "url": url,
            "status": resp.status,
            "content_length": len(content),
            "from_cache": False,
            "preview": content[:200].decode("utf-8", errors="replace"),
        }


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    try:
        result = fetch_live(url)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == 200 else 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc), "from_cache": False}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
