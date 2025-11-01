#!/bin/bash
#
# Install grpcui - Interactive gRPC Web UI
#
# grpcui provides a web interface for testing gRPC endpoints interactively,
# similar to Swagger UI for REST APIs. It can use server reflection or proto files.
#
# Official: https://github.com/fullstorydev/grpcui
#
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Default install directory
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
GRPCUI_VERSION="${GRPCUI_VERSION:-1.3.4}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Install grpcui - Interactive gRPC Web UI${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux)
    OS="linux"
    ;;
  Darwin)
    OS="darwin"
    ;;
  *)
    echo -e "${RED}❌ Unsupported OS: $OS${NC}"
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64)
    ARCH="amd64"
    ;;
  aarch64|arm64)
    ARCH="arm64"
    ;;
  *)
    echo -e "${RED}❌ Unsupported architecture: $ARCH${NC}"
    exit 1
    ;;
esac

# Check if Go is installed (preferred method)
if command -v go &> /dev/null; then
  echo -e "${GREEN}✓ Go found, installing via 'go install'${NC}"
  go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
  echo -e "${GREEN}✓ grpcui installed to $(go env GOPATH)/bin${NC}"
  exit 0
fi

# Fallback: download binary
echo -e "${YELLOW}⚠ Go not found, downloading binary instead${NC}"
echo ""

# Create install directory
mkdir -p "$INSTALL_DIR"

# Download URL
BINARY_NAME="grpcui_${GRPCUI_VERSION}_${OS}_${ARCH}"
DOWNLOAD_URL="https://github.com/fullstorydev/grpcui/releases/download/v${GRPCUI_VERSION}/${BINARY_NAME}.tar.gz"

echo "Downloading grpcui v${GRPCUI_VERSION}..."
echo "  OS: $OS"
echo "  Arch: $ARCH"
echo "  Destination: $INSTALL_DIR"
echo ""

# Download and extract
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

curl -sSL "$DOWNLOAD_URL" -o grpcui.tar.gz
tar -xzf grpcui.tar.gz
chmod +x grpcui

# Move to install directory
mv grpcui "$INSTALL_DIR/grpcui"
rm -rf "$TEMP_DIR"

# Verify installation
if [ -f "$INSTALL_DIR/grpcui" ]; then
  chmod +x "$INSTALL_DIR/grpcui"
  VERSION_OUTPUT=$("$INSTALL_DIR/grpcui" --version 2>&1 || echo "unknown")
  echo ""
  echo -e "${GREEN}✓ grpcui installed successfully${NC}"
  echo "  Version: $VERSION_OUTPUT"
  echo "  Location: $INSTALL_DIR/grpcui"
  echo ""
  echo "Add to PATH:"
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
  echo ""
  echo -e "${BLUE}Usage examples:${NC}"
  echo "  # With server reflection (if enabled on gRPC server)"
  echo "  grpcui -plaintext localhost:50055"
  echo ""
  echo "  # With proto files"
  echo "  grpcui -plaintext -protopath specs/fleet -proto orchestrator/v1/orchestrator.proto localhost:50055"
  echo ""
else
  echo -e "${RED}❌ Installation failed${NC}"
  exit 1
fi



