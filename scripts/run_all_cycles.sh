#!/usr/bin/env bash
# Run all A+ Hard Gate audit cycle verifications
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Cycle 1: Lexicon & Tokenization ==="
python3 scripts/verify_cycle1.py

echo "=== Cycle 2: Grammar (ANTLR) ==="
java -jar tools/antlr-4.13.1-complete.jar -Dlanguage=Python3 -o /tmp/antlr_out syntax/Frontier.g4
cargo run --release --bin frontier -- parse examples/sample.fr > /dev/null

echo "=== Cycle 3: Orthogonality ==="
python3 scripts/analyze_grammar.py

echo "=== Cycle 4: Semantic Resolution ==="
cargo run --release --bin frontier -- resolve examples/sample.fr > /dev/null

echo "=== Cycle 5: AST Hash & Round-Trip ==="
cargo run --release --bin frontier -- gen-artifacts
python3 scripts/test_roundtrip.py

echo "=== Cycle 6: Adversarial ==="
python3 scripts/test_redos.py
cargo run --release --bin frontier -- fuzz 1000000

echo ""
echo "ALL CYCLES PASS"
