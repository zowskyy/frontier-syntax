#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Local Coding Agent — Termux bootstrap (copy/paste into Termux)
set -euo pipefail

pkg update -y
pkg install -y python python-pip clang cmake git

resolve_python() {
  if command -v python3.12 >/dev/null 2>&1; then
    echo python3.12
    return 0
  fi
  ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [ "$ver" = "3.12" ]; then
    echo python3
    return 0
  fi
  if ! pkg search python3.12 2>/dev/null | grep -qE '^python3\.12/'; then
    pkg install -y tur-repo || true
    pkg update -y || true
  fi
  if pkg install -y python3.12 2>/dev/null && command -v python3.12 >/dev/null 2>&1; then
    echo python3.12
    return 0
  fi
  echo python3
}

PY="$(resolve_python)"
WHEEL_PY="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PIP="$PY -m pip"

echo "Using $PY (wheel tag cp${WHEEL_PY//./})"

$PIP install --user --upgrade pip wheel

$PIP install --user \
  --platform manylinux2014_aarch64 \
  --python-version "$WHEEL_PY" \
  --implementation cp \
  --only-binary=:all: \
  "pydantic>=2,<3" "pydantic-settings>=2,<3" typing-extensions annotated-types

WHEEL_URL="https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl"
$PIP install --user --no-deps "$WHEEL_URL"

export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

mkdir -p "$HOME/models"
agent benchmark --profile android
