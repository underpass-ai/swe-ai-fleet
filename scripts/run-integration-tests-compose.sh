#!/bin/bash
# Run integration tests using docker-compose/podman-compose
# No local Python dependencies required - everything runs in containers

set -e

# Detect container runtime
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
    echo "🐳 Using podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo "🐳 Using docker-compose"
else
    echo "❌ Error: Neither docker-compose nor podman-compose found"
    echo "Please install one of them:"
    echo "  - Podman: pip install podman-compose"
    echo "  - Docker: https://docs.docker.com/compose/install/"
    exit 1
fi

echo ""
echo "🔨 Building Orchestrator service image..."
if command -v podman &> /dev/null; then
    podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
      -f services/orchestrator/Dockerfile .
else
    docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
      -f services/orchestrator/Dockerfile .
fi

echo "✅ Image built successfully"

echo ""
echo "🚀 Starting services with $COMPOSE_CMD..."
cd tests/integration/services/orchestrator
$COMPOSE_CMD -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner

echo ""
echo "🧹 Cleaning up..."
$COMPOSE_CMD -f docker-compose.test.yml down -v

echo ""
echo "✅ Integration tests completed!"

