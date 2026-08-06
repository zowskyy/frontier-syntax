#!/usr/bin/env bash
# Sync agent-legal-record/ to private GitHub repo (run on YOUR machine with push access).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${AUDIT_REMOTE:-https://github.com/zowskyy/frontier-agent-legal-record.git}"
WORKDIR="${TMPDIR:-/tmp}/frontier-agent-legal-record-sync"

echo "Syncing $ROOT -> $REMOTE"
rm -rf "$WORKDIR"
git clone "$REMOTE" "$WORKDIR" 2>/dev/null || {
  mkdir -p "$WORKDIR"
  git -C "$WORKDIR" init -b main
  git -C "$WORKDIR" remote add origin "$REMOTE"
}

rsync -a --delete \
  --exclude '.git' \
  --exclude 'state/activity.json' \
  --exclude 'state/*.log' \
  "$ROOT/" "$WORKDIR/"

cd "$WORKDIR"
git add -A
if git diff --staged --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git commit -m "audit sync: $(date -u +%Y-%m-%dT%H:%MZ)"
git push -u origin main
echo "Pushed to $REMOTE"
