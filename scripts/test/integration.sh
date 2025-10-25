#!/bin/bash
# Run integration tests using podman-compose
# Levanta servicios reales (NATS, Redis, Neo4j, Orchestrator, Context) definidos en docker-compose
# Tests se comunican via network interno (NO a production cluster)
# 
# Nota: Los .proto se generan automáticamente dentro de los containers durante build

set -e

echo "🐳 Using Podman Compose for integration tests"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up containers..."
    podman-compose -f tests/integration/docker-compose.integration.yml down -v 2>/dev/null || true
}

# Register cleanup on exit
trap cleanup EXIT

# Start all services (Neo4j, Redis, NATS)
echo "🚀 Starting infrastructure services (Neo4j, Redis, NATS)..."
podman-compose -f tests/integration/docker-compose.integration.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for all services to be ready..."

# Check Neo4j
for i in {1..30}; do
    if podman-compose -f tests/integration/docker-compose.integration.yml exec neo4j cypher-shell -u neo4j -p testpassword "RETURN 1" &>/dev/null; then
        echo "✅ Neo4j is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Neo4j failed to start in time"
        podman-compose -f tests/integration/docker-compose.integration.yml logs neo4j
        exit 1
    fi
    sleep 1
done

# Check Redis
for i in {1..30}; do
    if podman-compose -f tests/integration/docker-compose.integration.yml exec redis redis-cli ping &>/dev/null; then
        echo "✅ Redis is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Redis failed to start in time"
        podman-compose -f tests/integration/docker-compose.integration.yml logs redis
        exit 1
    fi
    sleep 1
done

# Check NATS
for i in {1..30}; do
    if podman-compose -f tests/integration/docker-compose.integration.yml exec nats nc -zv localhost 4222 &>/dev/null; then
        echo "✅ NATS is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ NATS failed to start in time"
        podman-compose -f tests/integration/docker-compose.integration.yml logs nats
        exit 1
    fi
    sleep 1
done

# Export environment variables for tests
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=testpassword
export REDIS_HOST=localhost
export REDIS_PORT=6379
export NATS_URL=nats://localhost:4222

echo ""
echo "🧪 Running integration tests..."
echo "Environment:"
echo "  NEO4J_URI=$NEO4J_URI"
echo "  REDIS_HOST=$REDIS_HOST"
echo "  NATS_URL=$NATS_URL"
echo ""

# Run pytest with integration marker (excluding e2e tests which require Kubernetes cluster)
# E2E tests are now in tests/e2e/ so they won't interfere
python -m pytest tests/integration -m "integration and not e2e" -v --tb=short

echo ""
echo "✅ Integration tests completed successfully!"
echo ""
echo "💡 Note: E2E tests are in tests/e2e/"
echo "   Run with: pytest tests/e2e -m e2e"

