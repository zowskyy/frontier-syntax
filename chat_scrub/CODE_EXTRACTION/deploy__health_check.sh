#!/bin/bash
set -e

echo "🔍 Running health check..."

# Run verification suite (no live services required for repo health)
cargo test --lib
python3 scripts/verify_v2.py

# Optional service checks when endpoints are configured
if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
  echo "✅ frontier-api healthy"
fi
if curl -sf http://localhost:8081/health >/dev/null 2>&1; then
  echo "✅ frontier-migration healthy"
fi
if curl -sf http://localhost:8082/health >/dev/null 2>&1; then
  echo "✅ frontier-lsp healthy"
fi

echo "✅ All systems healthy"
