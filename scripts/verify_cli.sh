#!/usr/bin/env bash
# Frontier CLI verification suite — proves all CLI features work end-to-end.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🔨 Building release binary..."
cargo build --release --bin frontier 2>&1

FRONTIER="./target/release/frontier"

echo ""
echo "📋 Testing --help..."
$FRONTIER --help > /dev/null

echo "📋 Testing completions..."
$FRONTIER completions bash > /tmp/frontier_completions.bash
test -s /tmp/frontier_completions.bash

echo "📋 Testing config init..."
rm -f frontier.toml
$FRONTIER config init
test -f frontier.toml
$FRONTIER config show > /dev/null

echo "📋 Testing knowledge suggest..."
$FRONTIER knowledge suggest sort list::i32 > /dev/null

echo "📋 Testing compile with profile..."
$FRONTIER compile examples/v2_parser_test.fr -t wasm -O -p > /dev/null
test -f examples/v2_parser_test.wasm

echo "📋 Testing parse-v2..."
$FRONTIER parse-v2 examples/v2_parser_test.fr > /dev/null

echo "📋 Testing hash..."
$FRONTIER hash examples/sample.fr > /dev/null

echo ""
echo "✅ ALL CLI FEATURES VERIFIED"
