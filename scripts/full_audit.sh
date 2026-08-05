#!/usr/bin/env bash
# Full audit — runs all verification gates and cargo tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🔍 Frontier v2.0 Full Audit"
echo "==========================="

python3 scripts/verify_all.py
cargo test --lib
coqc proofs/double_proof.v
python3 scripts/verify_v2.py

echo ""
echo "✅ Full audit complete"
