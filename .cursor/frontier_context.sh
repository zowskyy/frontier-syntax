#!/usr/bin/env bash
# Load Frontier master skill context for Cursor AI sessions.
# Usage: .cursor/frontier_context.sh [--full]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_FILE="$SCRIPT_DIR/skills/frontier-master.md"

if [ ! -f "$SKILL_FILE" ]; then
  echo "ERROR: frontier-master skill not found at $SKILL_FILE" >&2
  exit 1
fi

echo "Frontier Master Skill — context loader"
echo "Repository: $REPO_ROOT"
echo "Skill: $SKILL_FILE"
echo ""

if [ "${1:-}" = "--full" ]; then
  cat "$SKILL_FILE"
  exit 0
fi

# Compact context for agent prompts: overview, commands, and current priorities.
sed -n '/^## 1\. Project Overview/,/^---$/p' "$SKILL_FILE" | sed '$d'
echo ""
sed -n '/^## 7\. Key Commands/,/^---$/p' "$SKILL_FILE" | sed '$d'
echo ""
sed -n '/^## 6\. Remaining Work/,/^---$/p' "$SKILL_FILE" | sed '$d'
echo ""
echo "Full skill: .cursor/skills/frontier-master.md"
echo "Full dump:  .cursor/frontier_context.sh --full"
echo "Audit:      .cursor/frontier_agent.sh all"
