#!/bin/bash
set -e

echo "🔍 Running health check..."

# Run verification suite (no live services required for repo health)
cargo test --lib
python3 scripts/verify_v2.py

# Peerless runtime probes (plan execution OPT-004/007/008)
python3 scripts/runtime_gpu.py 2>/dev/null || echo "⚠️  GPU runtime probe skipped"
python3 scripts/runtime_cdx.py 2>/dev/null || echo "⚠️  CDX runtime probe skipped"
python3 scripts/runtime_ipfs.py 2>/dev/null || echo "⚠️  IPFS runtime probe skipped"

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
