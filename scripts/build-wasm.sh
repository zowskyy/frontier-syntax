#!/usr/bin/env bash
# Build Frontier WASM artifacts for Lighthouse browser-compiler.js
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "🔨 Building frontier-wasm (wasm32-unknown-unknown)..."
rustup target add wasm32-unknown-unknown 2>/dev/null || true

cargo build --release -p frontier-wasm --target wasm32-unknown-unknown

OUT_DIR="$ROOT/wasm-playground"
mkdir -p "$OUT_DIR"

cp "$ROOT/target/wasm32-unknown-unknown/release/frontier_wasm.wasm" "$OUT_DIR/wasm_parser.wasm"
cp "$ROOT/target/wasm32-unknown-unknown/release/frontier_wasm.wasm" "$OUT_DIR/wasm_compiler.wasm"
cp "$ROOT/target/wasm32-unknown-unknown/release/frontier_wasm.wasm" "$OUT_DIR/frontier_compiler.wasm"

echo "✅ WASM artifacts:"
ls -lh "$OUT_DIR"/*.wasm
echo ""
echo "Sync to Lighthouse: ./scripts/sync-to-lighthouse.sh"
