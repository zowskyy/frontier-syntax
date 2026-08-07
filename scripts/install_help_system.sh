#!/usr/bin/env bash
# Install the Get Help system into any git repo (including this one).
set -euo pipefail

TARGET="${1:-.}"
TARGET=$(cd "$TARGET" && pwd)
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SOURCE_REPO=$(cd "$SCRIPT_DIR/.." && pwd)

echo "📦 Installing Get Help system into: $TARGET"

# Copy help_system package
mkdir -p "$TARGET/scripts/help_system"
cp -r "$SOURCE_REPO/scripts/help_system/"* "$TARGET/scripts/help_system/"

# Copy entry point if missing
if [ ! -f "$TARGET/scripts/get_help.py" ]; then
  cp "$SOURCE_REPO/scripts/get_help.py" "$TARGET/scripts/get_help.py"
  chmod +x "$TARGET/scripts/get_help.py"
fi

# Per-repo config
mkdir -p "$TARGET/manifest"
if [ ! -f "$TARGET/manifest/help_config.json" ]; then
  REPO_NAME=$(basename "$TARGET")
  cat > "$TARGET/manifest/help_config.json" << EOF
{
  "repo_id": "$REPO_NAME",
  "repo_name": "$REPO_NAME",
  "labels": ["get-help"],
  "auto_create_github": true
}
EOF
  echo "   Created manifest/help_config.json"
fi

# Cursor integration
mkdir -p "$TARGET/.cursor/commands" "$TARGET/.cursor/skills"
if [ ! -f "$TARGET/.cursor/commands/get-help.md" ]; then
  cp "$SOURCE_REPO/.cursor/commands/get-help.md" "$TARGET/.cursor/commands/get-help.md"
fi
if [ ! -f "$TARGET/.cursor/skills/help-triage.md" ]; then
  cp "$SOURCE_REPO/.cursor/skills/help-triage.md" "$TARGET/.cursor/skills/help-triage.md"
fi

# Global registry dir
mkdir -p "$HOME/.frontier/help"

# Register repo
cd "$TARGET"
python3 scripts/get_help.py register 2>/dev/null || true

echo ""
echo "✅ Get Help installed!"
echo ""
echo "Usage:"
echo "  cd $TARGET"
echo '  python3 scripts/get_help.py "describe your problem"'
echo "  python3 scripts/get_help.py blocked"
echo "  python3 scripts/get_help.py status"
echo ""
echo "In Cursor: /get-help"
