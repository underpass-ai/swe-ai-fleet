#!/bin/bash
# Run Orchestrator Service integration tests with Docker/Podman
# All tests run in containers with API generated during build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Orchestrator Service Integration Tests"
echo "=========================================="
echo ""

# Auto-detect compose command
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ No compose tool found"
    echo "Install one of:"
    echo "  - pip install podman-compose (for Podman)"
    echo "  - docker-compose or docker compose (Docker)"
    exit 1
fi

echo "✅ Using: $COMPOSE_CMD"
echo ""

# Build images
echo "🏗️  Building images..."
$COMPOSE_CMD -f tests/integration/services/orchestrator/docker-compose.integration.yml build --no-cache
echo ""

# Start infrastructure services
echo "🚀 Starting infrastructure services..."
$COMPOSE_CMD -f tests/integration/services/orchestrator/docker-compose.integration.yml up -d nats redis orchestrator
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
podman ps --filter "name=orchestrator-e2e" --format "table {{.ID}}\t{{.Image}}\t{{.Command}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}"
echo ""

# Show service logs (last 5 lines each)
echo "📋 Service logs (last 5 lines each):"
echo ""
echo "--- NATS ---"
podman logs orchestrator-e2e-nats --tail 5 2>&1 | tail -5
echo ""
echo "--- Redis ---"
podman logs orchestrator-e2e-redis --tail 5 2>&1 | tail -5
echo ""
echo "--- Orchestrator Service ---"
podman logs orchestrator-e2e-service --tail 10 2>&1 | tail -10
echo ""

# Test connectivity from host
echo "🔌 Testing connectivity from host..."
nc -zv localhost 24222 2>&1 | grep -q succeeded && echo "  NATS (24222): ✅" || echo "  NATS (24222): ❌"
nc -zv localhost 26379 2>&1 | grep -q succeeded && echo "  Redis (26379): ✅" || echo "  Redis (26379): ❌"
nc -zv localhost 50055 2>&1 | grep -q succeeded && echo "  Orchestrator (50055): ✅" || echo "  Orchestrator (50055): ❌"
echo ""

# Run E2E tests in container
echo "🧪 Running E2E tests in container..."
echo "=============================="
podman ps --filter "name=orchestrator-e2e" --format "{{.Names}}"
$COMPOSE_CMD -f tests/integration/services/orchestrator/docker-compose.integration.yml run --rm tests
TEST_EXIT_CODE=$?
echo ""

# Cleanup
echo "🧹 Cleaning up..."
$COMPOSE_CMD -f tests/integration/services/orchestrator/docker-compose.integration.yml down -v
podman network prune -f
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed!"
    exit $TEST_EXIT_CODE
fi

