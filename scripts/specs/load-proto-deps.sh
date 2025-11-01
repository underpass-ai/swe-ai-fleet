#!/bin/bash
#
# Proto Dependency Loader
#
# Downloads and extracts proto bundle from registry for use during service builds.
# Supports version pinning and fallback to local specs for development.
#
# Usage:
#   ./scripts/specs/load-proto-deps.sh --service=orchestrator --version=1.0.0
#   ./scripts/specs/load-proto-deps.sh --service=context --local
#   ./scripts/specs/load-proto-deps.sh --service=all --version=1.0.0
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
REGISTRY="${REGISTRY:-registry.underpassai.com}"
IMAGE_NAME="${IMAGE_NAME:-swe-fleet/protos}"
SERVICE=""
VERSION=""
USE_LOCAL=false
OUTPUT_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --service=*)
      SERVICE="${1#*=}"
      shift
      ;;
    --version=*)
      VERSION="${1#*=}"
      shift
      ;;
    --local)
      USE_LOCAL=true
      shift
      ;;
    --output=*)
      OUTPUT_DIR="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--service=<name>] [--version=X.Y.Z] [--local] [--output=<dir>]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proto Dependency Loader${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Determine operation mode
if [ "$USE_LOCAL" = true ]; then
    echo -e "${BLUE}Mode: Local development (using local specs)${NC}"
    SOURCE_DIR="$SPECS_DIR/fleet"
else
    if [ -z "$VERSION" ]; then
        if [ -f "$SPECS_DIR/VERSION" ]; then
            VERSION=$(cat "$SPECS_DIR/VERSION")
            echo -e "${BLUE}Using version from specs/VERSION: $VERSION${NC}"
        else
            echo -e "${RED}❌ No version specified and VERSION file not found${NC}"
            exit 1
        fi
    else
        echo -e "${BLUE}Using specified version: $VERSION${NC}"
    fi
    
    echo -e "${BLUE}Mode: Remote (downloading from registry)${NC}"
    FULL_IMAGE="$REGISTRY/$IMAGE_NAME:v$VERSION"
fi

echo ""

# Set output directory
if [ -z "$OUTPUT_DIR" ]; then
    if [ "$USE_LOCAL" = true ]; then
        OUTPUT_DIR="$SPECS_DIR/fleet"
    else
        OUTPUT_DIR="/tmp/proto-deps-${VERSION}"
    fi
fi

# Local mode: copy specs directly
if [ "$USE_LOCAL" = true ]; then
    echo -e "${BLUE}Copying local proto files...${NC}"
    
    if [ "$SERVICE" = "all" ] || [ -z "$SERVICE" ]; then
        echo -e "${GREEN}✓ All proto files available locally${NC}"
        OUTPUT_DIR="$SPECS_DIR/fleet"
    else
        if [ -d "$SPECS_DIR/fleet/$SERVICE" ]; then
            mkdir -p "$OUTPUT_DIR/$SERVICE"
            cp -r "$SPECS_DIR/fleet/$SERVICE"/* "$OUTPUT_DIR/$SERVICE/"
            echo -e "${GREEN}✓ Copied $SERVICE proto files${NC}"
        else
            echo -e "${RED}❌ Service not found: $SERVICE${NC}"
            exit 1
        fi
    fi
else
    # Remote mode: download from registry
    echo -e "${BLUE}Downloading proto bundle from registry...${NC}"
    
    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        echo -e "${RED}❌ podman is not installed${NC}"
        exit 1
    fi
    
    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT
    
    # Pull image
    echo -e "${BLUE}Pulling $FULL_IMAGE...${NC}"
    if ! podman pull "$FULL_IMAGE" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Image not found in registry, falling back to local${NC}"
        USE_LOCAL=true
        SOURCE_DIR="$SPECS_DIR/fleet"
    else
        echo -e "${GREEN}✓ Image pulled${NC}"
        
        # Extract bundle
        echo -e "${BLUE}Extracting bundle...${NC}"
        podman create --name proto-extract "$FULL_IMAGE" > /dev/null 2>&1 || true
        
        # Copy bundle out
        mkdir -p "$OUTPUT_DIR"
        if podman cp proto-extract:/proto-bundle.bin "$TEMP_DIR/bundle.bin" 2>/dev/null; then
            # Extract from bundle (if using tar format)
            cd "$TEMP_DIR"
            tar -xzf bundle.bin 2>/dev/null || {
                # Might be plain protobuf bundle
                cp bundle.bin "$OUTPUT_DIR/proto-bundle.bin"
            }
            
            # Move extracted files to output
            if [ -d "$TEMP_DIR/fleet" ]; then
                cp -r "$TEMP_DIR/fleet" "$OUTPUT_DIR/"
            fi
            
            podman rm proto-extract > /dev/null 2>&1 || true
            echo -e "${GREEN}✓ Bundle extracted${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not extract bundle, falling back to local${NC}"
            USE_LOCAL=true
        fi
    fi
fi

# Filter by service if specified
if [ -n "$SERVICE" ] && [ "$SERVICE" != "all" ]; then
    if [ "$USE_LOCAL" = true ]; then
        if [ -d "$OUTPUT_DIR/$SERVICE" ]; then
            echo ""
            echo -e "${GREEN}✓ Proto files for $SERVICE loaded${NC}"
            echo "  Location: $OUTPUT_DIR/$SERVICE"
        else
            echo -e "${RED}❌ Service not found: $SERVICE${NC}"
            exit 1
        fi
    else
        if [ -d "$OUTPUT_DIR/fleet/$SERVICE" ]; then
            mkdir -p "$OUTPUT_DIR/$SERVICE"
            cp -r "$OUTPUT_DIR/fleet/$SERVICE"/* "$OUTPUT_DIR/$SERVICE/"
            rm -rf "$OUTPUT_DIR/fleet"
            echo ""
            echo -e "${GREEN}✓ Proto files for $SERVICE loaded${NC}"
            echo "  Location: $OUTPUT_DIR/$SERVICE"
        else
            echo -e "${RED}❌ Service not found in bundle: $SERVICE${NC}"
            exit 1
        fi
    fi
else
    echo ""
    echo -e "${GREEN}✓ All proto files loaded${NC}"
    echo "  Location: $OUTPUT_DIR"
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Proto dependencies loaded${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Proto files ready for generation."
echo ""
echo "Next steps in Dockerfile:"
echo '  python -m grpc_tools.protoc \'
echo '    --proto_path=/app/specs \'
echo '    --python_out=/app/gen \'
echo '    --grpc_python_out=/app/gen \'
echo "    $SERVICE/v1/${SERVICE}.proto"



