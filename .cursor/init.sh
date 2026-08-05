#!/usr/bin/env bash
# Cursor AI initialization — load Frontier ecosystem context
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -x ".cursor/frontier_context.sh" ]; then
    .cursor/frontier_context.sh
fi
