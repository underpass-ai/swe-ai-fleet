#!/bin/bash
#
# Version Bump Utility
#
# Bumps the proto API version according to semantic versioning.
# Automatically detects change type and suggests appropriate version bump.
#
# Usage:
#   ./scripts/specs/version-bump.sh patch   # Bump patch version
#   ./scripts/specs/version-bump.sh minor   # Bump minor version
#   ./scripts/specs/version-bump.sh major   # Bump major version
#   ./scripts/specs/version-bump.sh auto    # Auto-detect and bump
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <patch|minor|major|auto>"
    exit 1
fi

BUMP_TYPE="$1"

if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major|auto)$ ]]; then
    echo -e "${RED}❌ Invalid bump type: $BUMP_TYPE${NC}"
    echo "Valid types: patch, minor, major, auto"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"
VERSION_FILE="$SPECS_DIR/VERSION"

cd "$SPECS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proto API Version Bump${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Read current version
if [ ! -f "$VERSION_FILE" ]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

CURRENT_VERSION=$(cat "$VERSION_FILE")
echo -e "${BLUE}Current version: $CURRENT_VERSION${NC}"

# Validate current version format
if ! [[ $CURRENT_VERSION =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo -e "${RED}❌ Invalid version format: $CURRENT_VERSION${NC}"
    exit 1
fi

MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"

# Auto-detect bump type
if [ "$BUMP_TYPE" = "auto" ]; then
    echo ""
    echo -e "${BLUE}Auto-detecting bump type...${NC}"
    
    # Check for breaking changes using buf
    if command -v buf &> /dev/null && [ -d "$PROJECT_ROOT/.git" ]; then
        if git rev-parse --verify main >/dev/null 2>&1; then
            if buf breaking --against '.git#branch=main' 2>/dev/null; then
                NO_BREAKING=true
            else
                NO_BREAKING=false
            fi
        else
            NO_BREAKING=true  # Can't check, assume no breaking changes
        fi
    else
        NO_BREAKING=true
    fi
    
    if [ "$NO_BREAKING" = false ]; then
        BUMP_TYPE="major"
        echo -e "${RED}⚠️  Breaking changes detected → MAJOR bump${NC}"
    else
        # Check if any .proto files changed
        if [ -d "$PROJECT_ROOT/.git" ]; then
            if git diff --quiet main -- "$SPECS_DIR/fleet/" 2>/dev/null; then
                BUMP_TYPE="patch"
                echo -e "${BLUE}Only metadata changed → PATCH bump${NC}"
            else
                BUMP_TYPE="minor"
                echo -e "${BLUE}Proto files modified → MINOR bump${NC}"
            fi
        else
            BUMP_TYPE="minor"
            echo -e "${BLUE}Assuming non-breaking changes → MINOR bump${NC}"
        fi
    fi
fi

# Calculate new version
case "$BUMP_TYPE" in
    patch)
        NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
        ;;
    minor)
        NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
        ;;
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
esac

echo ""
echo -e "${BLUE}Bump type: $BUMP_TYPE${NC}"
echo -e "${GREEN}New version: $NEW_VERSION${NC}"
echo ""

# Confirm
echo -e "${YELLOW}Update version? (y/n)${NC}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Update version file
echo "$NEW_VERSION" > "$VERSION_FILE"
echo -e "${GREEN}✓ Version updated${NC}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Version bumped successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Previous: $CURRENT_VERSION"
echo "Current:  $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. Commit the version change"
echo "  2. Run validation: ./scripts/specs/validate-protos.sh"
echo "  3. Publish bundle: ./scripts/specs/publish-proto-bundle.sh"



