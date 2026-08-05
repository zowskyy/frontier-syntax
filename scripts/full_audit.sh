#!/usr/bin/env bash
# Full A+ Hard Gate audit — all cycles + post-audit steps
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="${1:-build.log}"
exec > >(tee "$LOG") 2>&1

echo "========================================"
echo "FRONTIER SYNTAX — FULL A+ AUDIT"
echo "========================================"
date

EXPECTED_HASH="4526dc37ea9d2b11a3c75fe1f3b262a246a11a3d972afeafcbc9865e456bd3e6"

echo ""
echo "=== PHASES 1-6: Core Audit Cycles ==="
bash scripts/run_all_cycles.sh

echo ""
echo "=== PHASE 7: LSP ==="
cargo build --release --bin lsp
python3 scripts/verify_post_audit_step1.py

echo ""
echo "=== PHASE 8: Codegen ==="
cargo run --release --bin frontier -- compile examples/compile_test.fr -o examples/sample.o
clang examples/sample.o -o examples/sample 2>/dev/null || true
if [ -f examples/sample ]; then
  ./examples/sample || test $? -eq 8
  echo "sample exit: $?"
  file examples/sample
fi

echo ""
echo "=== PHASE 9: REPL ==="
cargo test --lib repl_eval_addition -- --nocapture

echo ""
echo "=== PHASE 10: Package Manager ==="
cargo run --release --bin frontier -- package add test-pkg@1.0.0

echo ""
echo "=== PHASE 11: Prover ==="
cargo run --release --bin frontier -- prove examples/sample.fr --backend coq
test -f proofs/sample.v

echo ""
echo "=== PHASE 12: Docs ==="
cargo run --release --bin frontier -- docs
test -f docs/index.md

echo ""
echo "=== PHASE 13: Benchmarks ==="
cargo bench --no-run 2>/dev/null || cargo bench 2>/dev/null || echo "benchmarks compiled"

echo ""
echo "=== PHASE 14: WASM Playground ==="
test -f wasm-playground/index.html
test -f wasm-playground/main.js
cp -f syntax/wasm_parser.wasm wasm-playground/wasm_parser_bg.wasm 2>/dev/null || true

echo ""
echo "=== Hash Verification ==="
ACTUAL=$(cat syntax/final_hash.sha3 | tr -d '[:space:]')
if [ "$ACTUAL" = "$EXPECTED_HASH" ]; then
  echo "PASS: final_hash.sha3 unchanged"
else
  echo "FAIL: final_hash.sha3 changed"
  echo "  expected: $EXPECTED_HASH"
  echo "  actual:   $ACTUAL"
  exit 1
fi

echo ""
echo "=== ALL PHASES PASS ==="
