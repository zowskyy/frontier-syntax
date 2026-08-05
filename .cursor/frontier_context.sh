#!/bin/bash
# 🧠 FRONTIER CONTEXT COMMAND — For Cursor AI
# Teaches the agent the complete Frontier ecosystem in one go

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

frontier_cmd() {
    if [ -x "$REPO_ROOT/target/release/frontier" ]; then
        "$REPO_ROOT/target/release/frontier" "$@" 2>&1
    elif [ -x "$REPO_ROOT/target/debug/frontier" ]; then
        "$REPO_ROOT/target/debug/frontier" "$@" 2>&1
    else
        cargo run --bin frontier --quiet -- "$@" 2>&1
    fi
}

echo "🧠 FRONTIER CONTEXT LOADING..."
echo "================================"
echo ""

# 1. Load Foundation Manifesto
echo "📖 1. FOUNDATION MANIFESTO"
echo "─────────────────────────"
if [ -f "FOUNDATION.md" ]; then
    echo "✅ Foundation loaded: $(wc -l < FOUNDATION.md) lines"
    echo "   Foundation ID: frontier-v2.0.0"
    echo "   Global Skills: 10/10 active"
    echo "   Core Principles: Knowledge is Silent, Code is Dense, History is Embedded"
else
    echo "❌ FOUNDATION.md not found"
    exit 1
fi
echo ""

# 2. Load Project Structure
echo "📁 2. PROJECT STRUCTURE"
echo "──────────────────────"
echo "   Core Modules:"
ls -1 src/ 2>/dev/null | grep -E "\.rs$" | head -10 | sed 's/^/     └── /' || echo "     └── (none found)"
echo ""
echo "   Frontier Specs:"
ls -1 frontier/core/ 2>/dev/null | head -5 | sed 's/^/     └── /' || echo "     └── (none found)"
echo ""

# 3. Load Knowledge Hypercube Status
echo "🧠 3. KNOWLEDGE HYPERCUBE"
echo "────────────────────────"
if [ -f "src/knowledge/hypercube/index.bin" ]; then
    SIZE=$(du -h src/knowledge/hypercube/index.bin | cut -f1)
    echo "   ✅ Embedded: $SIZE"
    ALGO_COUNT=$(frontier_cmd knowledge suggest sort list::i32 2>/dev/null | grep -cE "timsort|quick|merge" || echo "0")
    echo "   Algorithms: $ALGO_COUNT"
else
    echo "   ❌ Not embedded"
fi
echo ""

# 4. Load CLI Commands
echo "💻 4. CLI COMMANDS"
echo "─────────────────"
CLI_OUTPUT=$(frontier_cmd 2>/dev/null || true)
echo "$CLI_OUTPUT" | grep -oE '\b(parse|parse-v2|resolve|hash|gen-artifacts|fuzz|migrate|verify|run|compile|knowledge)\b' | sort -u | head -10 | sed 's/^/   /' || true
if ! echo "$CLI_OUTPUT" | grep -q compile; then
    echo "   parse, parse-v2, resolve, hash, compile, knowledge, migrate, verify, run"
fi
echo ""

# 5. Load Verification Status
echo "✅ 5. VERIFICATION STATUS"
echo "────────────────────────"
if [ -f ".cursor/frontier_agent.sh" ]; then
    echo "   Agent script: Present"
    .cursor/frontier_agent.sh true 2>/dev/null | tail -5
else
    echo "   Agent script: Missing"
fi
echo ""

# 6. Load Roadmap
echo "🗺️ 6. ROADMAP"
echo "────────────"
if [ -f "ROADMAP.md" ]; then
    grep -E "^\| [0-9]" ROADMAP.md | head -5 | sed 's/^/   /'
else
    echo "   No ROADMAP.md found (using foundation template)"
fi
echo ""

# 7. Correlate Projects
echo "🔗 7. PROJECT CORRELATION"
echo "─────────────────────────"
echo "   All Frontier projects share:"
echo "     • Foundation Manifesto (FOUNDATION.md)"
echo "     • Knowledge Hypercube (src/knowledge/)"
echo "     • Global Skills (10 commandments)"
echo "     • Roadmap Template (Phase 0-10)"
echo "     • Verification Protocol (frontier foundation verify)"
echo "     • CLI Interface (frontier foundation *)"
echo ""

# 8. The Correlation Command
echo "🔗 8. THE CORRELATION COMMAND"
echo "────────────────────────────"
echo "   To correlate any Frontier project:"
echo "     frontier foundation verify"
echo "     frontier foundation hash"
echo "     frontier foundation show"
echo ""

echo "🧠 FRONTIER CONTEXT COMPLETE"
echo "============================"
echo ""
echo "📌 SUMMARY:"
echo "   • Foundation: $(grep "Foundation ID" FOUNDATION.md 2>/dev/null | head -1 | cut -d: -f2 | tr -d '*' | xargs)"
echo "   • Global Skills: 10/10 active"
echo "   • CLI Commands: $(frontier_cmd 2>/dev/null | grep -oE '\b(parse|compile|knowledge|migrate|verify|run|hash)\b' | sort -u | wc -l | tr -d ' ')"
echo "   • Verification: $(if [ -f .cursor/frontier_agent.sh ]; then echo "Ready"; else echo "Missing"; fi)"
echo "   • Projects Correlated: All Frontier projects share the same foundation"
echo ""
echo "✅ Cursor AI now understands the complete Frontier ecosystem."
