#!/usr/bin/env bash
# Push Frontier-Syntax assets into a Lighthouse checkout
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIGHTHOUSE_HOME="${LIGHTHOUSE_HOME:-$(dirname "$ROOT")/mia.loa}"
DEST="$LIGHTHOUSE_HOME/public/syntax"

if [[ ! -d "$LIGHTHOUSE_HOME" ]]; then
  echo "❌ Lighthouse not found at $LIGHTHOUSE_HOME"
  echo "   Set LIGHTHOUSE_HOME to your mia.loa checkout"
  exit 1
fi

mkdir -p "$DEST"

for file in token_regex_table.json lexicon.ebnf grammar.g4 ast_sample.json; do
  if [[ -f "$ROOT/syntax/$file" ]]; then
    cp "$ROOT/syntax/$file" "$DEST/$file"
    echo "✅ $file"
  fi
done

if [[ -f "$ROOT/syntax/cycle2/extensions.json" ]]; then
  cp "$ROOT/syntax/cycle2/extensions.json" "$DEST/cycle2_extensions.json"
  echo "✅ cycle2_extensions.json"
fi

for wasm in wasm-playground/wasm_parser.wasm wasm-playground/wasm_compiler.wasm; do
  if [[ -f "$ROOT/$wasm" ]]; then
    cp "$ROOT/$wasm" "$DEST/$(basename "$wasm")"
    echo "✅ $(basename "$wasm")"
  fi
done

echo ""
echo "Done — assets in $DEST"
echo "Lighthouse: node assemble.js --item wasm-compiler"
