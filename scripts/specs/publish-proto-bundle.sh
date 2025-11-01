#!/bin/bash
#
# Publish Proto Bundle to OCI Registry
#
# Builds a proto bundle and publishes it to the container registry as an OCI artifact.
# This enables versioned proto distribution and ensures compatibility across services.
#
# Usage:
#   ./scripts/specs/publish-proto-bundle.sh                   # Use version from specs/VERSION
#   ./scripts/specs/publish-proto-bundle.sh --dry-run         # Test without publishing
#   ./scripts/specs/publish-proto-bundle.sh --version=1.2.0   # Override version
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
DRY_RUN=false
VERSION_OVERRIDE=""
REGISTRY="${REGISTRY:-registry.underpassai.com}"
IMAGE_NAME="${IMAGE_NAME:-swe-fleet/protos}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --version=*)
      VERSION_OVERRIDE="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run] [--version=X.Y.Z]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"

cd "$SPECS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proto Bundle Publishing${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
if ! command -v buf &> /dev/null; then
    echo -e "${RED}❌ buf is not installed${NC}"
    exit 1
fi

if ! command -v podman &> /dev/null; then
    echo -e "${RED}❌ podman is not installed${NC}"
    exit 1
fi

# Get version
if [ -n "$VERSION_OVERRIDE" ]; then
    VERSION="$VERSION_OVERRIDE"
    echo -e "${BLUE}Using override version: $VERSION${NC}"
else
    if [ -f "VERSION" ]; then
        VERSION=$(cat VERSION)
        echo -e "${BLUE}Using version from VERSION file: $VERSION${NC}"
    else
        echo -e "${RED}❌ VERSION file not found${NC}"
        exit 1
    fi
fi

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid version format: $VERSION${NC}"
    exit 1
fi

FULL_IMAGE="$REGISTRY/$IMAGE_NAME:v$VERSION"
echo ""

# Step 1: Validate protos
echo -e "${BLUE}Step 1: Validating proto files...${NC}"
bash "$SCRIPT_DIR/validate-protos.sh" --no-breaking || {
    echo -e "${RED}❌ Validation failed${NC}"
    exit 1
}
echo ""

# Step 2: Build proto bundle
echo -e "${BLUE}Step 2: Building proto bundle...${NC}"
BUNDLE_FILE="proto-bundle-${VERSION}.bin"
rm -f "$BUNDLE_FILE"

if buf build -o "$BUNDLE_FILE"; then
    BUNDLE_SIZE=$(du -h "$BUNDLE_FILE" | cut -f1)
    echo -e "${GREEN}✓ Bundle built: $BUNDLE_FILE (${BUNDLE_SIZE})${NC}"
else
    echo -e "${RED}❌ Failed to build bundle${NC}"
    exit 1
fi
echo ""

# Step 3: Create OCI manifest and push (or simulate)
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⏭️  DRY RUN - Skipping push${NC}"
    echo ""
    echo "Would push to: $FULL_IMAGE"
    echo "Bundle: $BUNDLE_FILE"
else
    echo -e "${BLUE}Step 3: Publishing to registry...${NC}"
    
    # Note: For now, we'll create a container image with the bundle
    # In production, you'd use OCI artifacts (simpler than implementing OCI artifacts from scratch)
    cat > /tmp/Dockerfile.proto-bundle << EOF
FROM scratch
COPY $BUNDLE_FILE /proto-bundle.bin
COPY VERSION /VERSION
LABEL org.opencontainers.image.title="SWE AI Fleet Proto Bundle"
LABEL org.opencontainers.image.version="$VERSION"
LABEL org.opencontainers.image.description="Protocol Buffer definitions bundle for SWE AI Fleet"
LABEL org.opencontainers.image.created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF
    
    # Build and push
    cd "$SPECS_DIR"
    podman build -t "$FULL_IMAGE" -f /tmp/Dockerfile.proto-bundle . || {
        echo -e "${RED}❌ Failed to build container image${NC}"
        exit 1
    }
    
    podman push "$FULL_IMAGE" || {
        echo -e "${RED}❌ Failed to push to registry${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Published: $FULL_IMAGE${NC}"
fi
echo ""

# Step 4: Generate and display SHA256
echo -e "${BLUE}Step 4: Generating checksums...${NC}"
SHA256=$(sha256sum "$BUNDLE_FILE" | cut -d' ' -f1)
echo -e "${GREEN}✓ SHA256: ${SHA256}${NC}"
echo ""

# Step 5: Update changelog if exists
if [ -f "CHANGELOG.md" ]; then
    echo -e "${BLUE}Step 5: Changelog detected (updating skipped, manual process)${NC}"
fi
echo ""

# Cleanup
rm -f "$BUNDLE_FILE" /tmp/Dockerfile.proto-bundle

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Proto bundle published successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Image: $FULL_IMAGE"
echo "SHA256: ${SHA256}"
echo ""
echo "Services can now reference this version:"
echo "  PROTO_VERSION=$VERSION"



