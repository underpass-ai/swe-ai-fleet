#!/bin/bash
#
# Install Buf - Protocol Buffer Linter and Breaking Change Detector
#
# Usage:
#   ./scripts/install-buf.sh
#
# This script installs Buf CLI tool which is used for:
# - Linting protobuf files
# - Detecting breaking changes
# - Generating code from protos
# - Managing proto dependencies

set -e

# Configuration
BUF_VERSION="${BUF_VERSION:-1.40.1}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
TMP_DIR="/tmp/buf-install-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
info() {
    echo -e "${GREEN}ℹ${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Detect OS and architecture
detect_platform() {
    OS=$(uname -s)
    ARCH=$(uname -m)
    
    case "$OS" in
        Linux*)
            OS_NAME="Linux"
            ;;
        Darwin*)
            OS_NAME="Darwin"
            ;;
        *)
            error "Unsupported operating system: $OS"
            ;;
    esac
    
    case "$ARCH" in
        x86_64)
            ARCH_NAME="x86_64"
            ;;
        aarch64|arm64)
            ARCH_NAME="aarch64"
            ;;
        *)
            error "Unsupported architecture: $ARCH"
            ;;
    esac
    
    info "Detected platform: $OS_NAME $ARCH_NAME"
}

# Check if buf is already installed
check_existing() {
    if command -v buf &> /dev/null; then
        CURRENT_VERSION=$(buf --version | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
        warn "Buf is already installed: $CURRENT_VERSION"
        read -p "Do you want to reinstall/upgrade to v${BUF_VERSION}? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Installation cancelled"
            exit 0
        fi
    fi
}

# Check write permissions
check_permissions() {
    if [ ! -w "$INSTALL_DIR" ]; then
        error "No write permission to $INSTALL_DIR. Try running with sudo or set INSTALL_DIR to a writable location."
    fi
}

# Download and install buf
install_buf() {
    info "Installing Buf v${BUF_VERSION}..."
    
    # Create temporary directory
    mkdir -p "$TMP_DIR"
    cd "$TMP_DIR"
    
    # Construct download URL
    DOWNLOAD_URL="https://github.com/bufbuild/buf/releases/download/v${BUF_VERSION}/buf-${OS_NAME}-${ARCH_NAME}"
    
    info "Downloading from: $DOWNLOAD_URL"
    
    # Download
    if ! curl -fsSL "$DOWNLOAD_URL" -o buf; then
        error "Failed to download Buf from $DOWNLOAD_URL"
    fi
    
    # Make executable
    chmod +x buf
    
    # Move to install directory
    if [ -w "$INSTALL_DIR" ]; then
        mv buf "$INSTALL_DIR/buf"
        success "Buf installed to $INSTALL_DIR/buf"
    else
        sudo mv buf "$INSTALL_DIR/buf"
        success "Buf installed to $INSTALL_DIR/buf (with sudo)"
    fi
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TMP_DIR"
}

# Verify installation
verify_installation() {
    info "Verifying installation..."
    
    if ! command -v buf &> /dev/null; then
        error "Buf installation failed - command not found in PATH"
    fi
    
    INSTALLED_VERSION=$(buf --version)
    success "Buf installed successfully!"
    echo "  Version: $INSTALLED_VERSION"
    echo "  Location: $(which buf)"
}

# Create buf config if not exists
create_config_hint() {
    if [ ! -f "specs/buf.yaml" ]; then
        echo ""
        info "Next steps:"
        echo "  1. Create specs/buf.yaml configuration"
        echo "  2. Run: buf lint specs/fleet"
        echo "  3. Run: buf breaking --against '.git#branch=main'"
        echo ""
        echo "See API_VERSIONING_IMPLEMENTATION.md for details"
    fi
}

# Main installation flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════╗"
    echo "║  Buf Installation Script                      ║"
    echo "║  Protocol Buffer Linter & Breaking Detector   ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    
    detect_platform
    check_existing
    check_permissions
    install_buf
    verify_installation
    create_config_hint
    
    echo ""
    success "Installation complete! 🎉"
}

# Run main function
main "$@"

