#!/data/data/com.termux/files/usr/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
# rollback revert undo migration downgrade — production rollback path
# Local Coding Agent — Termux bootstrap (Python 3.12 + binary wheels only)
set -euo pipefail

pkg update -y
# Termux default python (3.13) often lacks pydantic-core wheels on Android; use 3.12.
pkg install -y python-3.12 clang cmake git

PY=python3.12
PIP="$PY -m pip"

$PIP install --user --upgrade pip wheel

# Force manylinux aarch64 wheels — avoids Rust/maturin build on device.
$PIP install --user \
  --platform manylinux2014_aarch64 \
  --python-version 3.12 \
  --implementation cp \
  --only-binary=:all: \
  "pydantic>=2,<3" "pydantic-settings>=2,<3" typing-extensions annotated-types

WHEEL_URL="https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl"
$PIP install --user --no-deps "$WHEEL_URL"

export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

mkdir -p "$HOME/models"
agent benchmark --profile android
