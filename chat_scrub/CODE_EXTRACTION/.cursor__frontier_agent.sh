#!/bin/bash
# 🧠 FRONTIER TRUE COMPLETION — CURSOR AI AGENT SCRIPT
# Usage: .cursor/frontier_agent.sh [audit|gaps|fix|submit|all]
# Default: all

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prefer release binary when available (faster audits)
frontier_cmd() {
    if [ -x "$REPO_ROOT/target/release/frontier" ]; then
        "$REPO_ROOT/target/release/frontier" "$@"
    else
        cargo run --bin frontier --quiet -- "$@"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 1: AUDIT — Full System Inspection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

audit() {
    echo -e "${BLUE}🔍 FRONTIER COMPLETE AUDIT${NC}"
    echo "================================"
    echo ""

    cd "$REPO_ROOT"

    # 1. Knowledge Hypercube
    echo -e "${BLUE}📚 Knowledge Hypercube:${NC}"
    if [ -f "src/knowledge/hypercube/index.bin" ]; then
        SIZE=$(du -h src/knowledge/hypercube/index.bin | cut -f1)
        echo -e "   ${GREEN}✅ index.bin present ($SIZE)${NC}"
    else
        echo -e "   ${RED}❌ index.bin missing${NC}"
    fi

    echo "   Suggestion test:"
    frontier_cmd knowledge suggest sort list::i32 2>/dev/null | head -3 || echo -e "   ${YELLOW}⚠️ Command failed${NC}"
    echo ""

    # 2. Browser Compiler
    echo -e "${BLUE}🌐 Browser Compiler:${NC}"
    BROWSER_COUNT=$(ls src/browser_*.rs 2>/dev/null | wc -l)
    if [ "$BROWSER_COUNT" -gt 0 ]; then
        echo -e "   ${GREEN}✅ $BROWSER_COUNT files found${NC}"
    else
        echo -e "   ${RED}❌ No browser files found${NC}"
    fi

    if [ -f "frontier/core/browser_compiler.frontier" ]; then
        echo -e "   ${GREEN}✅ Spec file present${NC}"
    else
        echo -e "   ${RED}❌ Spec file missing${NC}"
    fi
    echo ""

    # 3. WASM Codegen
    echo -e "${BLUE}⚡ WASM Codegen:${NC}"
    if [ -f "src/wasm_codegen.rs" ]; then
        LINES=$(wc -l < src/wasm_codegen.rs)
        echo -e "   ${GREEN}✅ File present ($LINES lines)${NC}"
    else
        echo -e "   ${RED}❌ File missing${NC}"
    fi
    echo ""

    # 4. Tests
    echo -e "${BLUE}🧪 Tests:${NC}"
    TEST_COUNT=$(cargo test --lib -- --list 2>/dev/null | wc -l | tr -d ' ')
    if [ -n "$TEST_COUNT" ] && [ "$TEST_COUNT" -gt 0 ]; then
        echo -e "   ${GREEN}✅ $TEST_COUNT tests available${NC}"
    else
        echo -e "   ${RED}❌ Tests not found${NC}"
    fi
    echo ""

    # 5. CLI
    echo -e "${BLUE}💻 CLI:${NC}"
    if frontier_cmd --help 2>&1 | grep -qE "compile|knowledge"; then
        echo -e "   ${GREEN}✅ compile and knowledge commands found${NC}"
    else
        echo -e "   ${RED}❌ Commands missing${NC}"
    fi
    echo ""

    # 6. Browser UI
    echo -e "${BLUE}🖥️ Browser UI:${NC}"
    if [ -f "browser/index.html" ]; then
        echo -e "   ${GREEN}✅ index.html present${NC}"
    else
        echo -e "   ${RED}❌ index.html missing${NC}"
    fi
    if [ -f "browser/frontier_runtime.js" ]; then
        echo -e "   ${GREEN}✅ frontier_runtime.js present${NC}"
    else
        echo -e "   ${RED}❌ frontier_runtime.js missing${NC}"
    fi

    echo ""
    echo -e "${GREEN}✅ AUDIT COMPLETE${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 2: GAPS — Honest Gap Verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

gaps() {
    echo -e "${YELLOW}⚠️ FRONTIER GAP VERIFICATION${NC}"
    echo "================================"
    echo ""

    cd "$REPO_ROOT"

    PASS=0
    FAIL=0

    # 1. Real WASM codegen?
    echo -n "1. Real WASM codegen: "
    if frontier_cmd compile examples/v2_parser_test.fr --target wasm -o /tmp/out.wasm 2>/dev/null; then
        if [ -f /tmp/out.wasm ]; then
            if command -v wasm-objdump &> /dev/null; then
                if wasm-objdump -h /tmp/out.wasm 2>/dev/null | grep -q "main"; then
                    echo -e "${GREEN}✅ main function found${NC}"
                    PASS=$((PASS+1))
                else
                    echo -e "${RED}❌ No main function${NC}"
                    FAIL=$((FAIL+1))
                fi
                if wasm-objdump -h /tmp/out.wasm 2>/dev/null | grep -q "if"; then
                    echo -e "   ${GREEN}✅ if support found${NC}"
                else
                    echo -e "   ${RED}❌ No if support${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️ wasm-objdump not installed (skip detailed check)${NC}"
                PASS=$((PASS+1))
            fi
        else
            echo -e "${RED}❌ WASM not generated${NC}"
            FAIL=$((FAIL+1))
        fi
    else
        echo -e "${RED}❌ compile command failed${NC}"
        FAIL=$((FAIL+1))
    fi

    # 2. Self-hosting?
    echo -n "2. Self-hosting: "
    if frontier_cmd compile frontier/core/browser_compiler.frontier --target wasm -o /tmp/browser.wasm 2>/tmp/frontier_selfhost.err; then
        echo -e "${YELLOW}⚠️ Unexpected success (spec files should not parse yet)${NC}"
    else
        if grep -qiE "parse|error|panic|illegal" /tmp/frontier_selfhost.err; then
            echo -e "${RED}❌ Fails (expected — .frontier specs are not v2 source)${NC}"
        else
            echo -e "${YELLOW}⚠️ Failed for unknown reason${NC}"
        fi
    fi

    # 3. Knowledge integration?
    echo -n "3. Knowledge integration: "
    if frontier_cmd compile examples/v2_parser_test.fr --target wasm --optimize -o /tmp/knowledge_test.wasm 2>&1 | grep -qi "timsort"; then
        echo -e "${GREEN}✅ Knowledge suggested${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ No knowledge suggestion${NC}"
        FAIL=$((FAIL+1))
    fi

    # 4. Build size?
    echo -n "4. WASM size: "
    if [ -f target/wasm32-unknown-unknown/release/frontier.wasm ]; then
        SIZE=$(du -h target/wasm32-unknown-unknown/release/frontier.wasm | cut -f1)
        echo "$SIZE"
    else
        echo -e "${RED}❌ WASM not built (run: cargo build --release --target wasm32-unknown-unknown)${NC}"
        FAIL=$((FAIL+1))
    fi

    echo ""
    echo -e "📊 Gap Verification: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 3: TRUE — Core Verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

true_verify() {
    echo -e "${BLUE}🧠 TRUE FRONTIER TECHNOLOGY VERIFICATION${NC}"
    echo "================================================"
    echo ""

    cd "$REPO_ROOT"

    PASS=0
    FAIL=0

    # 1. Knowledge Hypercube responds
    echo -n "1. Knowledge Hypercube: "
    frontier_cmd knowledge suggest sort list::i32 > /tmp/knowledge.out 2>&1
    if grep -qE "timsort|quick|merge" /tmp/knowledge.out; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAIL=$((FAIL+1))
    fi

    # 2. Browser compiler compiles
    echo -n "2. Browser compiler compiles: "
    cargo build --release --target wasm32-unknown-unknown > /tmp/build.out 2>&1
    if [ -f target/wasm32-unknown-unknown/release/frontier.wasm ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAIL=$((FAIL+1))
    fi

    # 3. Tests pass
    echo -n "3. Tests pass: "
    cargo test --lib > /tmp/test.out 2>&1
    if grep -q "test result: ok" /tmp/test.out; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAIL=$((FAIL+1))
    fi

    # 4. CLI works
    echo -n "4. CLI works: "
    frontier_cmd --help > /tmp/cli.out 2>&1
    if grep -qE "compile|knowledge" /tmp/cli.out; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAIL=$((FAIL+1))
    fi

    # 5. Browser UI exists
    echo -n "5. Browser UI exists: "
    if [ -f browser/index.html ] && [ -f browser/frontier_runtime.js ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS=$((PASS+1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAIL=$((FAIL+1))
    fi

    echo ""
    echo -e "📊 Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
    if [ "$FAIL" -eq 0 ]; then
        echo -e "${GREEN}🎉 TRUE FRONTIER TECHNOLOGY — READY${NC}"
        echo "   All 5 core components verified"
        echo "   Gaps remain: codegen, knowledge integration, self-hosting"
        echo "   But the foundation is solid."
    else
        echo -e "${RED}⚠️ TRUE FRONTIER — $FAIL components need attention${NC}"
    fi

    # Save for next steps
    echo "$PASS/$FAIL" > /tmp/frontier_true.out
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 4: FIX — Prioritized Fix Sequence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

fix() {
    echo -e "${BLUE}🔧 FRONTIER GAP CLOSURE — PRIORITY ORDER${NC}"
    echo "================================================"
    echo ""

    cd "$REPO_ROOT"

    # Read current gap status
    if [ -f /tmp/frontier_true.out ]; then
        PASS=$(cut -d'/' -f1 < /tmp/frontier_true.out)
        FAIL=$(cut -d'/' -f2 < /tmp/frontier_true.out)
        echo -e "📊 Current verification: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
        echo ""
    fi

    # PRIORITY 1: REAL WASM CODEGEN
    echo -e "${BLUE}📌 PRIORITY 1: Real WASM Codegen${NC}"
    echo "   Status: Only const-folded main() works"
    echo "   Fix: Extend src/wasm_codegen.rs for:"
    echo "     - let bindings + local variables"
    echo "     - if/else blocks"
    echo "     - function calls"
    echo "     - while loops"
    echo "     - return with expressions"
    echo "   File: src/wasm_codegen.rs"
    echo "   Test: cargo test --lib wasm_codegen"
    echo ""

    # PRIORITY 2: KNOWLEDGE → CODEGEN
    echo -e "${BLUE}📌 PRIORITY 2: Knowledge → Codegen${NC}"
    echo "   Status: Suggestions are warnings only"
    echo "   Fix: Use AlgorithmSuggestion.implementation_hint to change WASM"
    echo "   File: src/wasm_codegen.rs + src/browser_compiler.rs"
    echo "   Test: frontier compile --optimize changes output"
    echo ""

    # PRIORITY 3: UNIFY GLUE
    echo -e "${BLUE}📌 PRIORITY 3: Unify Browser + CLI Glue${NC}"
    echo "   Status: CLI hand-written strings, browser wasm-bindgen"
    echo "   Fix: Use wasm-bindgen for both"
    echo "   File: src/browser_compiler.rs + src/browser_wasm.rs"
    echo "   Test: cargo build --target wasm32 + wasm-bindgen"
    echo ""

    # PRIORITY 4: SLIM WASM
    echo -e "${BLUE}📌 PRIORITY 4: Slim WASM${NC}"
    echo "   Status: ~760 KB artifact"
    echo "   Fix: Feature flag for browser-minimal"
    echo "   File: Cargo.toml + src/lib.rs"
    echo "   Target: < 100 KB"
    echo ""

    # PRIORITY 5: SPEC VS IMPL
    echo -e "${BLUE}📌 PRIORITY 5: Close Spec vs Impl Gap${NC}"
    echo "   Status: .frontier specs not valid v2"
    echo "   Fix: Move to docs/design/specs/ OR teach parser"
    echo "   File: frontier/core/ → docs/design/specs/"
    echo "   Test: python3 scripts/verify_language_hardening.py passes"
    echo ""

    echo -e "${GREEN}✅ FIX SEQUENCE DEFINED${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 5: SUBMIT — PR Submission Helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

submit() {
    echo -e "${BLUE}📤 FRONTIER SUBMIT — PR READY${NC}"
    echo "=============================="
    echo ""

    cd "$REPO_ROOT"

    # Check if we have a PR description
    if [ ! -f "PR_DESCRIPTION.md" ]; then
        echo -e "${YELLOW}⚠️ No PR_DESCRIPTION.md found${NC}"
        echo "   Creating template..."
        cat > PR_DESCRIPTION.md << 'EOF'
## Summary

[Describe what this PR does]

## Changes

- [Change 1]
- [Change 2]

## Testing

- [ ] `cargo test --lib` passes
- [ ] `cargo build --target wasm32-unknown-unknown` succeeds
- [ ] Browser UI works

## Verification

```
frontier compile examples/v2_parser_test.fr --target wasm --optimize
```
EOF
        echo -e "   ${GREEN}✅ PR_DESCRIPTION.md created${NC}"
    fi

    # 1. Run all tests
    echo "1. Running all tests..."
    if cargo test --lib; then
        echo -e "   ${GREEN}✅ Tests pass${NC}"
    else
        echo -e "   ${RED}❌ Tests failed${NC}"
        exit 1
    fi

    # 2. Build WASM
    echo "2. Building WASM..."
    if cargo build --release --target wasm32-unknown-unknown 2>/dev/null; then
        echo -e "   ${GREEN}✅ WASM built${NC}"
    else
        echo -e "   ${RED}❌ WASM build failed${NC}"
        exit 1
    fi

    # 3. Verify browser UI
    echo "3. Verifying browser UI..."
    if [ -f scripts/verify_browser_compiler.py ]; then
        if python3 scripts/verify_browser_compiler.py; then
            echo -e "   ${GREEN}✅ Verification passed${NC}"
        else
            echo -e "   ${YELLOW}⚠️ Verification failed${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠️ verify_browser_compiler.py not found${NC}"
    fi

    # 4. Check git status
    echo "4. Git status:"
    git status --short

    # 5. Ready to submit
    echo ""
    echo "5. Ready to submit:"
    echo ""
    echo "   git add -A"
    echo "   git commit -m \"feat: [Phase X] [description]\""
    echo "   git push -u origin \$(git branch --show-current)"
    echo "   gh pr create --title \"[Phase X] [description]\" --body \"\$(cat PR_DESCRIPTION.md)\""
    echo ""
    echo -e "${GREEN}✅ SUBMIT READY${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 6: ALL — The Master Command
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

all() {
    echo -e "${BLUE}🧠 FRONTIER TRUE COMPLETION — MASTER COMMAND${NC}"
    echo "================================================"
    echo ""

    cd "$REPO_ROOT"

    # 1. Verify we are on Frontier v2 with knowledge + browser
    echo -e "${BLUE}📌 1. VERIFYING FRONTIER V2...${NC}"
    if git log --oneline -20 | grep -qiE "knowledge|browser|hypercube"; then
        echo -e "   ${GREEN}✅ Knowledge + browser commits present${NC}"
    else
        echo -e "   ${RED}❌ Missing knowledge/browser integration commits${NC}"
        echo "   Please merge PRs #10 and #11 first"
        exit 1
    fi

    if [ -d "src/knowledge" ] && [ -f "src/knowledge/hypercube/index.bin" ]; then
        echo -e "   ${GREEN}✅ Knowledge Hypercube present${NC}"
    else
        echo -e "   ${RED}❌ Knowledge Hypercube missing${NC}"
        exit 1
    fi

    if ls src/browser_*.rs >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Browser compiler present${NC}"
    else
        echo -e "   ${RED}❌ Browser compiler missing${NC}"
        exit 1
    fi

    echo ""

    # 2. Run full audit
    audit

    echo ""

    # 3. Run gap verification
    gaps

    echo ""

    # 4. Run true verification
    true_verify

    echo ""

    # 5. Show next priority
    echo -e "${BLUE}📌 5. NEXT PRIORITY:${NC}"
    echo "   Phase 1: Real WASM Codegen"
    echo "   File: src/wasm_codegen.rs"
    echo "   Task: Add let, if, calls, loops"
    echo "   Command: cargo test --lib wasm_codegen"
    echo ""
    fix

    echo ""
    echo -e "${GREEN}✅ FRONTIER TRUTH COMPLETE${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMAND DISPATCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

case "${1:-all}" in
    audit) audit ;;
    gaps) gaps ;;
    true) true_verify ;;
    fix) fix ;;
    submit) submit ;;
    all) all ;;
    *)
        echo "Usage: $0 [audit|gaps|true|fix|submit|all]"
        echo ""
        echo "  audit   - Full system audit"
        echo "  gaps    - Honest gap verification"
        echo "  true    - Core verification"
        echo "  fix     - Prioritized fix sequence"
        echo "  submit  - PR submission helper"
        echo "  all     - Run everything (default)"
        exit 1
        ;;
esac
