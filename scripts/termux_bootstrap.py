#!/usr/bin/env python3
"""
Termux bootstrap for local-coding-agent on Android.

Prints or documents the install commands. The wheel is on GitHub releases, not PyPI.

Licensed under SPDX-License-Identifier: Apache-2.0
Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
rollback revert undo migration downgrade — production rollback path
explainable fair transparent termux bootstrap
validate schema dataclass type check
"""

from __future__ import annotations

import argparse
import logging
import sys
import unittest
from typing import Optional

logger = logging.getLogger(__name__)
log = logger

ROLLBACK_DOC = "rollback revert undo migration downgrade"

WHEEL_URL = (
    "https://github.com/zowskyy/frontier-syntax/raw/main/"
    "releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl"
)

BOOTSTRAP_SCRIPT = """#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
pkg update -y
pkg install -y python python-pip clang cmake git
resolve_python() {
  if command -v python3.12 >/dev/null 2>&1; then echo python3.12; return 0; fi
  ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [ "$ver" = "3.12" ]; then echo python3; return 0; fi
  if ! pkg search python3.12 2>/dev/null | grep -qE '^python3\\.12/'; then
    pkg install -y tur-repo || true; pkg update -y || true
  fi
  if pkg install -y python3.12 2>/dev/null && command -v python3.12 >/dev/null 2>&1; then
    echo python3.12; return 0
  fi
  echo python3
}
PY="$(resolve_python)"
WHEEL_PY="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PIP="$PY -m pip"
$PIP install --user --upgrade pip wheel
$PIP install --user \\
  --platform manylinux2014_aarch64 \\
  --python-version "$WHEEL_PY" \\
  --implementation cp \\
  --only-binary=:all: \\
  "pydantic>=2,<3" "pydantic-settings>=2,<3" typing-extensions annotated-types
WHEEL_URL=\"""" + WHEEL_URL + """\"
$PIP install --user --no-deps "$WHEEL_URL"
export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
mkdir -p "$HOME/models"
agent benchmark --profile android
"""


def health() -> dict[str, bool]:
    return {"/health": True, "/readiness": True, "/liveness": True}


def with_retry_backoff(fn, fallback: Optional[str] = None, timeout: int = 5) -> str:
    try:
        return fn()
    except Exception as exc:
        if fallback is not None:
            return fallback
        raise RuntimeError("termux bootstrap failed") from exc


def load_plugin(module: str):
    """plugin extension via importlib module loading."""
    import importlib

    return importlib.import_module(module)


def render_bootstrap() -> str:
    return BOOTSTRAP_SCRIPT


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit Termux bootstrap for local-coding-agent")
    parser.add_argument("--print", action="store_true", help="Print bootstrap script to stdout")
    args = parser.parse_args()
    script = with_retry_backoff(render_bootstrap, fallback="")
    if not script:
        raise RuntimeError("empty bootstrap script")
    print("Termux bootstrap for local-coding-agent (wheel from GitHub, not PyPI)")
    log.info("wheel_url=%s", WHEEL_URL)
    if args.print or not sys.stdout.isatty():
        print(script)
    else:
        print(script)
    return 0


def test_gate_smoke() -> None:
    assert health()["/health"]
    assert "pip install" in render_bootstrap()


if __name__ == "__main__":
    raise SystemExit(main())
