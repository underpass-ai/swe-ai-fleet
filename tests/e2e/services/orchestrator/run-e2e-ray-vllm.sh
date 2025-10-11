#!/bin/bash
set -e

echo "🧪 Orchestrator E2E Tests with Ray + vLLM"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

echo "🧹 Cleaning up previous containers..."
podman-compose -f docker-compose.ray-vllm.yml down -v 2>/dev/null || true

echo ""
echo "🏗️  Building containers..."
podman-compose -f docker-compose.ray-vllm.yml build

echo ""
echo "🚀 Starting services (Ray + vLLM + NATS + Redis + Orchestrator)..."
echo "   This will take ~2-3 minutes..."
echo ""

# Start all services
podman-compose -f docker-compose.ray-vllm.yml up -d

echo ""
echo "⏳ Waiting for all services to be healthy..."
echo "   (This can take up to 2 minutes for vLLM to download and load model)"
echo ""

# Wait for services with timeout
timeout 180 bash -c '
while true; do
    HEALTHY=$(podman ps --filter "name=orchestrator-e2e" --format "{{.Names}} {{.Status}}" | grep -c "healthy" || echo 0)
    TOTAL=$(podman ps --filter "name=orchestrator-e2e" --format "{{.Names}}" | wc -l)
    
    echo -ne "\r   Services healthy: $HEALTHY/$TOTAL   "
    
    if [ "$HEALTHY" -ge 4 ]; then
        echo ""
        break
    fi
    sleep 5
done
' || {
    echo -e "\n${RED}❌ Timeout waiting for services${NC}"
    echo ""
    echo "Service status:"
    podman ps --filter "name=orchestrator-e2e" --format "table {{.Names}}\t{{.Status}}"
    exit 1
}

echo -e "${GREEN}✅ All services ready${NC}"

echo ""
echo "🔍 Services status:"
podman ps --filter "name=orchestrator-e2e" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🧪 Running E2E tests..."
echo "=============================="
echo ""

# Run tests
podman-compose -f docker-compose.ray-vllm.yml run --rm tests || {
    TEST_EXIT=$?
    echo ""
    echo -e "${RED}❌ Tests failed with exit code $TEST_EXIT${NC}"
    echo ""
    echo "📋 Service logs (last 30 lines each):"
    echo ""
    echo "--- Orchestrator ---"
    podman logs orchestrator-e2e-service --tail 30
    echo ""
    echo "--- vLLM ---"
    podman logs orchestrator-e2e-vllm --tail 30
    echo ""
    echo "--- Ray ---"
    podman logs orchestrator-e2e-ray-head --tail 30
    
    echo ""
    echo "🧹 Cleaning up..."
    podman-compose -f docker-compose.ray-vllm.yml down -v
    exit $TEST_EXIT
}

echo ""
echo "🧹 Cleaning up..."
podman-compose -f docker-compose.ray-vllm.yml down -v

echo ""
echo -e "${GREEN}✅ All E2E tests passed!${NC}"
echo ""

