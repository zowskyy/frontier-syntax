#!/usr/bin/env bash
# Close out frontier-dex: verify gates, seal TRACKING.json, append event log.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "Frontier-DEX close-out"
echo "======================"

# 1. Run verification (must exist and pass)
if [[ ! -x "$ROOT/verify.sh" ]]; then
  echo "ERROR: $ROOT/verify.sh not found or not executable" >&2
  exit 1
fi

echo "[$(ts)] Running verify.sh ..."
"$ROOT/verify.sh"

# 2. Update TRACKING.json status to closed
if [[ ! -f "$ROOT/TRACKING.json" ]]; then
  echo "ERROR: TRACKING.json missing" >&2
  exit 1
fi

python3 - "$ROOT/TRACKING.json" <<'PY'
import json, sys
from datetime import datetime, timezone

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

data["status"] = "closed"
data["closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

# 3. Append close-out event
EVENTS="$ROOT/TRACKING_EVENTS.jsonl"
printf '%s\n' \
  "{\"ts\":\"$(ts)\",\"event\":\"project_closed\",\"actor\":\"closeout.sh\",\"detail\":\"verify.sh passed; TRACKING.json status=closed\"}" \
  >> "$EVENTS"

echo "[$(ts)] Close-out complete — status=closed"
echo "  TRACKING.json updated"
echo "  Event appended to TRACKING_EVENTS.jsonl"
echo "  See CERTIFICATION.md for gate evidence"
