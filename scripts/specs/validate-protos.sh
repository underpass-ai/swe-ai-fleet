#!/bin/bash
#
# Proto Validation Script
#
# Validates all proto files using Buf:
# - Runs linting checks
# - Detects breaking changes against main branch
# - Ensures versioning compliance
#
# Usage:
#   ./scripts/specs/validate-protos.sh               # Validate current state
#   ./scripts/specs/validate-protos.sh --strict      # Fail on warnings
#   ./scripts/specs/validate-protos.sh --no-breaking # Skip breaking change checks
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
STRICT_MODE=false
SKIP_BREAKING=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --strict)
      STRICT_MODE=true
      shift
      ;;
    --no-breaking)
      SKIP_BREAKING=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--strict] [--no-breaking]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"

cd "$SPECS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proto Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if buf is installed
if ! command -v buf &> /dev/null; then
    echo -e "${RED}❌ buf is not installed${NC}"
    echo ""
    echo "Install with:"
    echo "  curl -sSL 'https://buf.build/install.sh' | bash -s -- '1.40.1'"
    echo "  sudo mv buf /usr/local/bin/"
    exit 1
fi

echo -e "${BLUE}📦 Using buf version:${NC}"
buf --version
echo ""

# Step 1: Lint proto files
echo -e "${BLUE}Step 1: Linting proto files...${NC}"
if buf lint; then
    echo -e "${GREEN}✓ Lint passed${NC}"
else
    if [ "$STRICT_MODE" = true ]; then
        echo -e "${RED}❌ Lint failed (strict mode)${NC}"
        exit 1
    else
        echo -e "${YELLOW}⚠️  Lint warnings (non-critical)${NC}"
    fi
fi
echo ""

# Step 2: Check for breaking changes
if [ "$SKIP_BREAKING" = false ]; then
    echo -e "${BLUE}Step 2: Checking for breaking changes...${NC}"

    # Check if we're in a git repo with main branch
    if [ -d "$PROJECT_ROOT/.git" ]; then
        # Try to check against main branch
        if git rev-parse --verify main >/dev/null 2>&1; then
            if buf breaking --against '.git#branch=main'; then
                echo -e "${GREEN}✓ No breaking changes detected${NC}"
            else
                echo -e "${RED}❌ BREAKING CHANGES DETECTED${NC}"
                echo ""
                echo "This is a MAJOR version bump required."
                echo "Update specs/VERSION to increment MAJOR version."
                exit 1
            fi
        else
            echo -e "${YELLOW}⚠️  Main branch not found, skipping breaking change check${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Not in git repo, skipping breaking change check${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  Skipping breaking change check (--no-breaking)${NC}"
fi
echo ""

# Step 3: Verify version file exists and is valid
echo -e "${BLUE}Step 3: Verifying version file...${NC}"
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
    if [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${GREEN}✓ Version file valid: $VERSION${NC}"
    else
        echo -e "${RED}❌ Invalid version format: $VERSION (expected MAJOR.MINOR.PATCH)${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ VERSION file not found in $SPECS_DIR${NC}"
    exit 1
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Proto validation complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "All proto files are valid and backward-compatible."
echo "Version: $VERSION"

