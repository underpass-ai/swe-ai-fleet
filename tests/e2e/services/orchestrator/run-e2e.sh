#!/bin/bash
# Run Orchestrator Service E2E tests with podman-compose
# All tests run in containers with API generated during build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Orchestrator Service E2E Tests"
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
podman-compose -f tests/e2e/services/orchestrator/docker-compose.e2e.yml build --no-cache
echo ""

# Start infrastructure services
echo "🚀 Starting infrastructure services..."
podman-compose -f tests/e2e/services/orchestrator/docker-compose.e2e.yml up -d nats redis orchestrator
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
podman-compose -f tests/e2e/services/orchestrator/docker-compose.e2e.yml run --rm tests
TEST_EXIT_CODE=$?
echo ""

# Cleanup
echo "🧹 Cleaning up..."
podman-compose -f tests/e2e/services/orchestrator/docker-compose.e2e.yml down -v
podman network prune -f
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed!"
    exit $TEST_EXIT_CODE
fi

