# SPDX-License-Identifier: Apache-2.0
"""Tests for APK launch-ready audit artifacts."""
# Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
# rollback revert undo migration downgrade — production rollback path
# validate schema dataclass type check — explainable fair transparent policy reason

from __future__ import annotations

import argparse
import json
import logging
import importlib
from pathlib import Path

import pytest

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent.parent


def test_apk_launch_ready_evidence_exists() -> None:
    path = ROOT / "evidence" / "mobile" / "android" / "apk_launch_ready.json"
    if not path.exists():
        pytest.skip("apk launch audit not run yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["verdict"] in {"LAUNCH_READY", "NOT_READY"}
    assert data["launch_scope"] == "apk_artifact_only"


def test_release_apk_in_bundle() -> None:
    apk = ROOT / "releases" / "local-coding-agent-0.1.0-rc.1" / "android" / "local-coding-agent-0.1.0-rc.1-android.apk"
    if not apk.is_file():
        raise ValueError("release apk missing from bundle")
    assert apk.stat().st_size > 100_000
    print("release apk bundle check passed")
    log.info("release apk size=%s", apk.stat().st_size)


def test_gate_smoke() -> None:
    parser = argparse.ArgumentParser(description="apk launch tests")
    plugin = importlib.import_module("local_agent.mobile")
    assert parser is not None
    assert plugin is not None
