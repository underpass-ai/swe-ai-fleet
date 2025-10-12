#!/bin/bash
# Run Context Service integration tests with Docker/Podman
# All tests run in containers with API generated during build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Context Service Integration Tests"
echo "======================================"
echo ""

# Auto-detect compose command
if command -v $COMPOSE_CMD &> /dev/null; then
    COMPOSE_CMD="$COMPOSE_CMD"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither $COMPOSE_CMD nor docker-compose found"
    echo "Install one of:"
    echo "  - pip install $COMPOSE_CMD (for Podman)"
    echo "  - docker-compose (usually pre-installed with Docker)"
    exit 1
fi

echo "✅ Using: $COMPOSE_CMD"
echo ""

# Build images
echo "🏗️  Building images..."
$COMPOSE_CMD -f tests/integration/services/context/docker-compose.integration.yml build --no-cache
echo ""

# Start infrastructure services
echo "🚀 Starting infrastructure services..."
$COMPOSE_CMD -f tests/integration/services/context/docker-compose.integration.yml up -d neo4j redis nats context
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Check services status
echo "🔍 Checking services status..."
$COMPOSE_CMD -f tests/integration/services/context/docker-compose.integration.yml ps
echo ""

# Show service logs
echo "📋 Service logs (last 5 lines each):"
echo ""
echo "--- Neo4j ---"
podman logs context-e2e-neo4j --tail 5 2>&1 || echo "Neo4j not ready"
echo ""
echo "--- Redis ---"
podman logs context-e2e-redis --tail 5 2>&1 || echo "Redis not ready"
echo ""
echo "--- NATS ---"
podman logs context-e2e-nats --tail 5 2>&1 || echo "NATS not ready"
echo ""
echo "--- Context Service ---"
podman logs context-e2e-service --tail 10 2>&1 || echo "Context not ready"
echo ""

# Test connectivity (usando puertos mapeados en host para evitar conflictos con K8s)
echo "🔌 Testing connectivity from host..."
echo -n "  Neo4j (17687): "
timeout 2 bash -c "</dev/tcp/localhost/17687" && echo "✅" || echo "❌"
echo -n "  Redis (16379): "
timeout 2 bash -c "</dev/tcp/localhost/16379" && echo "✅" || echo "❌"
echo -n "  NATS (14222): "
timeout 2 bash -c "</dev/tcp/localhost/14222" && echo "✅" || echo "❌"
echo -n "  Context (50054): "
timeout 2 bash -c "</dev/tcp/localhost/50054" && echo "✅" || echo "❌"
echo ""

# Run tests in container
echo "🧪 Running E2E tests in container..."
echo "=============================="
$COMPOSE_CMD -f tests/integration/services/context/docker-compose.integration.yml run --rm tests

TEST_EXIT_CODE=$?

# Show logs on failure
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Tests failed! Showing full service logs:"
    echo ""
    echo "=== Context Service Logs ==="
    podman logs context-e2e-service
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
$COMPOSE_CMD -f tests/integration/services/context/docker-compose.integration.yml down -v

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    exit 0
else
    echo ""
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi
