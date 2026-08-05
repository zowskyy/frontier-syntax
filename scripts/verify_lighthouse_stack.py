#!/usr/bin/env python3
"""Verify Lighthouse in-house stack .frontier modules exist and are non-empty."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "lighthouse_stack.json"

def main():
    assert MANIFEST.exists(), f"Missing {MANIFEST}"
    manifest = json.loads(MANIFEST.read_text())
    missing = []
    for section in manifest["modules"].values():
        for name, rel in section.items():
            path = ROOT / rel
            if not path.exists() or path.stat().st_size < 50:
                missing.append(rel)
    if missing:
        raise SystemExit("Missing or empty modules:\n" + "\n".join(missing))
    print(f"PASS: Lighthouse stack ({len(missing) or sum(len(s) for s in manifest['modules'].values())} modules)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
