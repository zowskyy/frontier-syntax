#!/bin/bash
# Deploy Frontier Knowledge Engine — self-improving, continuous, action-driven
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🚀 Frontier Knowledge Engine Deployment"
echo "======================================"

# Step 1: Ensure on base branch with latest
BRANCH="${DEPLOY_BRANCH:-cursor/frontier-syntax-cycle1-e39f}"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# Step 2: Dependencies (optional — engine works without Redis/embeddings)
if [ -f requirements-knowledge-engine.txt ]; then
  pip3 install --quiet --user -r requirements-knowledge-engine.txt || true
fi

# Step 3: Build CLI
cargo build --bin frontier --quiet 2>/dev/null || cargo build --bin frontier

# Step 4: Full pipeline
python3 frontier_agent.py "Run chat scrub pipeline"

# Step 5: Install git hooks (daemon optional via INSTALL_DAEMON=1)
python3 scripts/install_scrub_daemon.py --hooks-only
if [ "${INSTALL_DAEMON:-0}" = "1" ]; then
  python3 scripts/install_scrub_daemon.py --interval "${SCRUB_INTERVAL:-3600}"
fi

# Step 6: MCP registration
cargo run --bin frontier --quiet -- mcp register --tool query_chat_knowledge

# Step 7: Verification
echo ""
echo "✅ Verification"
echo "---------------"
git log --oneline -3
echo ""
KNOWLEDGE_FILE="src/knowledge/hypercube/chat_knowledge.json"
if [ -f "$KNOWLEDGE_FILE" ]; then
  ENTRIES=$(python3 -c "import json; print(json.load(open('$KNOWLEDGE_FILE'))['entry_count'])")
  echo "Knowledge index: $ENTRIES entries"
else
  echo "FAIL: knowledge index missing"
  exit 1
fi

cargo run --bin frontier --quiet -- mcp list
python3 scripts/generate_tests_from_scrub.py --run
python3 scripts/generate_scrub_dashboard.py

echo ""
echo "🏁 Knowledge engine deployed successfully"
echo "   Dashboard: chat_scrub/dashboard.html"
echo "   Report:    chat_scrub/WORKER_REPORT.json"
