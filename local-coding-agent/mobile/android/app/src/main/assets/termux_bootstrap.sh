#!/data/data/com.termux/files/usr/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Local Coding Agent — Termux bootstrap (manylinux wheels via --target)
set -euo pipefail

pkg update -y
pkg install -y python python-pip clang cmake git

PY=python3
SITE="$("$PY" -m site --user-site)"
mkdir -p "$SITE"
PIP="$PY -m pip"

VER="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Using $PY ($VER) site-packages: $SITE"

# Do NOT upgrade pip on Termux — breaks the python-pip package.
# pydantic-core has no Android wheels; manylinux2014_aarch64 cp313 wheels work with --target.
"$PIP" install --target "$SITE" \
  --platform manylinux2014_aarch64 \
  --python-version "$VER" \
  --implementation cp \
  --only-binary=:all: \
  "pydantic==2.10.6" "pydantic-settings==2.7.1" "typing-extensions" "annotated-types"

WHEEL_URL="https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl"
"$PIP" install --target "$SITE" --no-deps "$WHEEL_URL"

export PATH="$HOME/.local/bin:$SITE/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

mkdir -p "$HOME/models"
agent benchmark --profile android
