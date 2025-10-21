#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

HOOK_DIR=".git/hooks"
HOOK_SOURCE="scripts/pre-commit-checks.sh"
HOOK_TARGET="$HOOK_DIR/pre-commit"

echo "🔧 Installing pre-commit hooks..."

# Verify we're in a git repository
if [ ! -d ".git" ]; then
  echo -e "${RED}❌ Not a git repository${NC}"
  echo "Run this script from the root of the repository"
  exit 1
fi

# Verify source script exists
if [ ! -f "$HOOK_SOURCE" ]; then
  echo -e "${RED}❌ Source script not found: $HOOK_SOURCE${NC}"
  exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Make source script executable
chmod +x "$HOOK_SOURCE"

# Check if hook already exists
if [ -f "$HOOK_TARGET" ] || [ -L "$HOOK_TARGET" ]; then
  echo -e "${YELLOW}⚠️  Pre-commit hook already exists${NC}"
  read -p "Overwrite? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
  fi
  rm -f "$HOOK_TARGET"
fi

# Create symlink
ln -sf "../../$HOOK_SOURCE" "$HOOK_TARGET"

echo -e "${GREEN}✅ Pre-commit hook installed successfully${NC}"
echo ""
echo "The hook will run automatically on 'git commit'"
echo ""
echo "Test it now:"
echo "  ./scripts/pre-commit-checks.sh"
echo ""
echo "To bypass the hook (not recommended):"
echo "  git commit --no-verify"
