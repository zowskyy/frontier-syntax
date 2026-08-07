#!/usr/bin/env python3
"""Security scan for Frontier agent layer (Phase 7)."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "agent_security_scan.json"

AGENT_FILES = [
    "frontier_agent.py",
    ".cursor/symbiotic_agents.py",
]

DANGEROUS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval()"),
    (re.compile(r"\bexec\s*\("), "exec()"),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True"),
    (re.compile(r"os\.system\s*\("), "os.system()"),
    (re.compile(r"pickle\.loads\s*\("), "pickle.loads()"),
]


def scan_file(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)), "present": False, "pass": False, "findings": ["missing"]}
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = []
    for pattern, label in DANGEROUS_PATTERNS:
        if pattern.search(text):
            findings.append(label)
    return {
        "path": str(path.relative_to(ROOT)),
        "present": True,
        "pass": len(findings) == 0,
        "findings": findings,
    }


def verify() -> dict:
    results = [scan_file(ROOT / rel) for rel in AGENT_FILES]
    ok = all(r["pass"] for r in results if r["present"]) and any(r["present"] for r in results)
    summary = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_agent_security.py",
        "pass": ok,
        "results": results,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = verify()
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
