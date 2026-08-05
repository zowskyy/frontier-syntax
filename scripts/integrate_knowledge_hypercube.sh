#!/bin/bash
# FRONTIER KNOWLEDGE HYPERCUBE — DIRECT INTEGRATION
# Run once inside the frontier-syntax project. Preserves existing lib/Cargo setup.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🧠 FRONTIER: Injecting Knowledge Hypercube into Syntax Library"
echo "================================================================"

mkdir -p src/knowledge/hypercube scripts/extractors tests/knowledge

echo ""
echo "🔧 Building knowledge index..."
python3 scripts/extractors/inject_knowledge.py

echo ""
echo "🔨 Building Frontier with integrated knowledge..."
cargo build --release

echo ""
echo "🧪 Running knowledge tests..."
cargo test knowledge --lib

echo ""
echo "✅ COMPLETE! Knowledge Hypercube is integrated into the Frontier syntax library."
ALGO_COUNT="$(python3 - <<'PY'
from scripts.extractors.inject_knowledge import ALGORITHMS, LANGUAGES, HARDWARE
print(len(ALGORITHMS), len(LANGUAGES), len(HARDWARE))
PY
)"
read -r ALGOS LANGS HW <<< "$ALGO_COUNT"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FRONTIER KNOWLEDGE HYPERCUBE — DEPLOYED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📦 Algorithms:        $ALGOS"
echo "  🌐 Languages:         $LANGS"
echo "  💻 Hardware profiles: $HW"
echo "  ⚡ Zero runtime dependencies (embedded index.bin)"
echo "  🤫 Silent dimensional optimization"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
