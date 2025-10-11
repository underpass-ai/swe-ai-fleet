#!/bin/bash
# Run Context Service E2E tests with podman-compose
# All tests run in containers with API generated during build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Context Service E2E Tests"
echo "=============================="
echo ""

# Check if podman-compose is installed
if ! command -v podman-compose &> /dev/null; then
    echo "❌ podman-compose not found"
    echo "Install: pip install podman-compose"
    exit 1
fi

echo "✅ podman-compose found: $(which podman-compose)"
echo ""

# Build images
echo "🏗️  Building images..."
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml build --no-cache
echo ""

# Start infrastructure services
echo "🚀 Starting infrastructure services..."
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d neo4j redis nats context
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
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml ps
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
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml run --rm tests

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
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml down -v

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    exit 0
else
    echo ""
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi
