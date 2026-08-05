#!/bin/bash
# build_truth.sh - Frontier truth verification entrypoint (v3 engine wrapper)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 -m verification.engine "$@"
