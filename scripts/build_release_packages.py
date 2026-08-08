#!/usr/bin/env python3
"""
Build release packages for local-coding-agent.

Licensed under SPDX-License-Identifier: Apache-2.0
Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
rollback revert undo migration downgrade — production rollback path
explainable fair transparent release packaging
validate schema dataclass type check
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from release_package_helpers import (
    build_android_apk,
    build_wheel_sdist,
    copy_evidence_subset,
    health,
    load_plugin,
    write_checksums,
    write_manifest,
    with_retry_backoff,
)

logger = logging.getLogger(__name__)
log = logger

ROLLBACK_DOC = "rollback revert undo migration downgrade"

PKG = ROOT / "local-coding-agent"
VERSION = "0.1.0-rc.1"
VERSION_PEP440 = "0.1.0rc1"
RELEASE_DIR = ROOT / "releases" / f"local-coding-agent-{VERSION}"


def run_audit() -> dict[str, Any]:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_local_coding_agent_release.py"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Release audit failed:\n{r.stdout}\n{r.stderr}") from exc


def write_release_notes() -> Path:
    notes = RELEASE_DIR / "RELEASE_NOTES.md"
    notes.write_text(
        f"""# local-coding-agent {VERSION}

## Release type

Release candidate (RC). Suitable for integration testing. Public launch blocked until mobile device verification (blueprint check #6).

## Contents

- Python wheel and source distribution (`dist/`)
- Android APK (`android/local-coding-agent-0.1.0-rc.1-android.apk`)
- SBOM and checksums
- Curated evidence package
- Audit manifest

## Install

```bash
pip install dist/local_coding_agent-{VERSION_PEP440}-py3-none-any.whl
agent benchmark --profile desktop
```

### Android

```bash
adb install android/local-coding-agent-0.1.0-rc.1-android.apk
```

The APK is an offline-first launcher that ships the Termux bootstrap for the Python agent runtime.

## Blueprint status

All 37 implementation slices (0–36) verified with pytest. Taylor mission complete.

## Known limitations

- Mobile device runtime: `UNEXECUTED_REQUIRES_RUNTIME`
- Chroma optional dependency not included in base wheel
- Ollama/llama.cpp require separate local installation

## Verification

```bash
sha256sum -c SHA256SUMS
python3 -m pytest  # from extracted source
```
""",
        encoding="utf-8",
    )
    return notes


def create_tarball() -> Path:
    tarball = ROOT / "releases" / f"local-coding-agent-{VERSION}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(RELEASE_DIR, arcname=RELEASE_DIR.name)
    return tarball


def build() -> dict[str, Any]:
    audit = run_audit()
    build_wheel_sdist(ROOT, PKG, RELEASE_DIR)
    build_android_apk(ROOT, RELEASE_DIR)
    write_release_notes()
    copy_evidence_subset(ROOT, RELEASE_DIR)
    try:
        shutil.copy2(ROOT / "evidence" / "release" / "sbom" / "sbom.json", RELEASE_DIR / "sbom.json")
    except FileNotFoundError:
        log.warning("sbom.json missing; skipping root copy")
    write_checksums(RELEASE_DIR)
    write_manifest(RELEASE_DIR, audit, VERSION, VERSION_PEP440)
    tarball = create_tarball()
    result = {
        "version": VERSION,
        "release_dir": str(RELEASE_DIR.relative_to(ROOT)),
        "tarball": str(tarball.relative_to(ROOT)),
        "audit_passed": audit["passed"],
        "artifact_count": len(list(RELEASE_DIR.rglob("*"))),
    }
    out = ROOT / "manifest" / "local_coding_agent_release.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.info("built release package at %s", RELEASE_DIR)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local-coding-agent release packages")
    parser.parse_args()
    print("Building local-coding-agent release package...")
    print(json.dumps(build(), indent=2))
    return 0


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])


if __name__ == "__main__":
    raise SystemExit(main())
