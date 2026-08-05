#!/usr/bin/env bash
# Frontier CLI — Live Demo Script
# Usage:
#   ./scripts/demo.sh           # Auto-run (great for recordings)
#   ./scripts/demo.sh --present # Pause between steps (great for live talks)

set -euo pipefail
cd "$(dirname "$0")/.."

PRESENT=false
[[ "${1:-}" == "--present" ]] && PRESENT=true

pause() {
    if $PRESENT; then
        echo ""
        read -rp "  ↵ Press Enter to continue..."
        echo ""
    else
        sleep 1
    fi
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

step() {
    echo "  → $1"
}

# ── Build ────────────────────────────────────────────────────────────────────
section "1 · BUILD"
step "Compiling release binary..."
cargo build --release --bin frontier 2>&1 | tail -1
FRONTIER="./target/release/frontier"
pause

# ── Help ─────────────────────────────────────────────────────────────────────
section "2 · CLI OVERVIEW"
step "frontier --help"
$FRONTIER --help
pause

# ── Source ───────────────────────────────────────────────────────────────────
section "3 · FRONTIER SOURCE"
step "examples/showcase.fr"
echo ""
sed 's/^/    /' examples/showcase.fr
pause

# ── Parse ────────────────────────────────────────────────────────────────────
section "4 · PARSE v2 AST"
step "frontier parse-v2 examples/showcase.fr"
$FRONTIER parse-v2 examples/showcase.fr | head -20
echo "    ... (truncated)"
pause

# ── Knowledge ────────────────────────────────────────────────────────────────
section "5 · KNOWLEDGE HYPERCUBE"
step "frontier knowledge suggest sort list::i32"
$FRONTIER knowledge suggest sort list::i32
pause

step "frontier knowledge ancestry sort"
$FRONTIER knowledge ancestry sort | head -12
echo "    ... (truncated)"
pause

# ── Compile ──────────────────────────────────────────────────────────────────
section "6 · COMPILE TO WASM (optimized + profiled)"
step "frontier compile examples/showcase.fr -t wasm -O -p"
$FRONTIER compile examples/showcase.fr -t wasm -O -p
pause

# ── Hash ─────────────────────────────────────────────────────────────────────
section "7 · CANONICAL AST HASH"
step "frontier hash examples/showcase.fr"
HASH=$($FRONTIER hash examples/showcase.fr)
echo "    SHA3-256: $HASH"
pause

# ── Config ───────────────────────────────────────────────────────────────────
section "8 · CONFIG"
rm -f frontier.toml
step "frontier config init && frontier config show"
$FRONTIER config init
$FRONTIER config show
pause

# ── Done ─────────────────────────────────────────────────────────────────────
section "✅ DEMO COMPLETE"
echo "  Frontier CLI v2.0 — ready to show."
echo ""
echo "  Quick commands for your audience:"
echo "    ./scripts/demo.sh --present"
echo "    ./target/release/frontier shell"
echo "    ./target/release/frontier watch examples -- -t wasm -O"
echo ""
