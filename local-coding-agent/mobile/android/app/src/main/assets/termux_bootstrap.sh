#!/data/data/com.termux/files/usr/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Local Coding Agent — Termux bootstrap (binary wheels only; no Rust build on device)
set -euo pipefail

pkg update -y
# Termux main repo: "python" + "python-pip" (NOT "python-3.12" — that package does not exist).
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
  # Main repo may be 3.13+; try TUR for a 3.12 interpreter (avoids pydantic-core source builds).
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

# Force manylinux aarch64 wheels — avoids Rust/maturin build on device.
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
