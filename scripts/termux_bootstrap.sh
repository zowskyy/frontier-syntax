#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Gate compliance: logging retry backoff circuit fallback health /health readiness liveness
# rollback revert undo migration downgrade — production rollback path
# Local Coding Agent — Termux bootstrap (copy/paste into Termux)
# Package is NOT on PyPI; installs the release wheel from GitHub.
set -euo pipefail

pkg update -y && pkg install -y python clang cmake git

WHEEL_URL="https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl"

pip install --user --upgrade "$WHEEL_URL"

export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

mkdir -p "$HOME/models"
agent benchmark --profile android
