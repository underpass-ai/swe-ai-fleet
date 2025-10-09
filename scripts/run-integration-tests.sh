#!/bin/bash
# Script to build container images and run integration tests
# Supports both Docker and Podman

set -e

# Detect container runtime
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    echo "🐳 Using Podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    echo "🐳 Using Docker"
else
    echo "❌ Error: Neither Docker nor Podman found"
    echo "Please install one of them:"
    echo "  - Podman: sudo dnf install podman (Fedora/RHEL)"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo ""
echo "🔨 Building Orchestrator container image..."
$CONTAINER_CMD build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .

echo "✅ Container image built successfully"

# For Podman, make sure the socket is available
if [ "$CONTAINER_CMD" = "podman" ]; then
    echo ""
    echo "🔧 Checking Podman socket..."
    
    # Start podman socket if not running
    if ! systemctl --user is-active --quiet podman.socket; then
        echo "Starting Podman socket service..."
        systemctl --user start podman.socket
    fi
    
    # Export DOCKER_HOST for Testcontainers
    export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
    export TESTCONTAINERS_RYUK_DISABLED="true"
    
    echo "✅ Podman socket ready at: $DOCKER_HOST"
fi

echo ""
echo "🧪 Running integration tests..."
pytest tests/integration/services/orchestrator/ \
  -v \
  -m integration \
  --tb=short

echo ""
echo "✅ Integration tests completed!"

