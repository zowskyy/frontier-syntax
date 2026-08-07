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

echo "📋 Testing compile --help..."
compile_help_out=$($FRONTIER compile --help)
printf '%s\n' "$compile_help_out" | grep -qi compile

echo "📋 Testing completions..."
$FRONTIER completions bash > /tmp/frontier_completions.bash
test -s /tmp/frontier_completions.bash
grep -q 'complete -F _frontier_completions' /tmp/frontier_completions.bash

echo "📋 Testing config init..."
rm -f frontier.toml
$FRONTIER config init
test -f frontier.toml
$FRONTIER config show > /dev/null

echo "📋 Testing config parse fallback (invalid TOML)..."
printf '%s\n' 'invalid toml {{{' > frontier.toml
$FRONTIER config show > /dev/null
rm -f frontier.toml

echo "📋 Testing knowledge suggest..."
$FRONTIER knowledge suggest sort list::i32 > /dev/null

echo "📋 Testing compile with profile..."
$FRONTIER compile examples/v2_parser_test.fr -t wasm -O -p > /dev/null
test -f examples/v2_parser_test.wasm

echo "📋 Testing parse-v2..."
$FRONTIER parse-v2 examples/v2_parser_test.fr > /dev/null

echo "📋 Testing hash..."
$FRONTIER hash examples/sample.fr > /dev/null

echo "📋 Testing telemetry logging..."
rm -f .frontier-telemetry.log
FRONTIER_TELEMETRY=1 $FRONTIER hash examples/sample.fr > /dev/null
test -f .frontier-telemetry.log
rm -f .frontier-telemetry.log

echo "📋 Testing mcp list (if available)..."
mcp_help_out=$($FRONTIER mcp --help 2>&1 || $FRONTIER mcp help 2>&1 || true)
if printf '%s\n' "$mcp_help_out" | grep -qE '(^|[[:space:]])list([[:space:]]|$)'; then
    $FRONTIER mcp list > /dev/null
else
    echo "   (skipped: mcp list not in help)"
fi

echo ""
echo "🧹 Cleaning up artifacts..."
rm -f frontier.toml
rm -f examples/v2_parser_test.wasm
rm -f /tmp/frontier_completions.bash
rm -f .frontier-telemetry.log

echo ""
echo "✅ ALL CLI FEATURES VERIFIED"
