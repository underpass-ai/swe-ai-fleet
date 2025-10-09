#!/bin/bash
# Run integration tests using plain podman (no compose needed)
# Zero local Python dependencies - everything runs in containers

set -e

echo "🐳 Using Podman for integration tests"

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up containers..."
    podman rm -f orchestrator-test 2>/dev/null || true
    podman rm -f orchestrator-test-runner 2>/dev/null || true
    podman network rm orchestrator-test-net 2>/dev/null || true
}

# Register cleanup on exit
trap cleanup EXIT

echo ""
echo "🔨 Building Orchestrator service image..."
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .

echo "✅ Service image built"

echo ""
echo "🔨 Building test runner image..."
podman build -t orchestrator-test-runner:latest \
  -f tests/integration/services/orchestrator/Dockerfile.test .

echo "✅ Test image built"

echo ""
echo "🌐 Creating test network..."
podman network create orchestrator-test-net 2>/dev/null || true

echo ""
echo "🚀 Starting Orchestrator service..."
podman run -d \
  --name orchestrator-test \
  --network orchestrator-test-net \
  -e GRPC_PORT=50055 \
  -e PYTHONUNBUFFERED=1 \
  localhost:5000/swe-ai-fleet/orchestrator:latest

echo "⏳ Waiting for service to be ready..."
for i in {1..30}; do
    if podman exec orchestrator-test python -c "import grpc; channel = grpc.insecure_channel('localhost:50055'); grpc.channel_ready_future(channel).result(timeout=1)" 2>/dev/null; then
        echo "✅ Service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to start in time"
        echo "Service logs:"
        podman logs orchestrator-test
        exit 1
    fi
    sleep 1
done

echo ""
echo "🧪 Running integration tests..."
podman run --rm \
  --name orchestrator-test-runner \
  --network orchestrator-test-net \
  -e ORCHESTRATOR_HOST=orchestrator-test \
  -e ORCHESTRATOR_PORT=50055 \
  orchestrator-test-runner:latest

echo ""
echo "✅ Integration tests completed successfully!"

