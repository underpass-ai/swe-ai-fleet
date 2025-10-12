#!/usr/bin/env bash
#
# Script para ejecutar tests de integración con Podman
#
# Este script:
# 1. Levanta servicios necesarios (Neo4j, Redis, NATS)
# 2. Espera a que estén ready
# 3. Ejecuta tests de integración
# 4. Limpia servicios

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect compose command
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}❌ Neither podman-compose nor docker-compose found${NC}"
    exit 1
fi

COMPOSE_FILE="tests/integration/docker-compose.integration.yml"

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Integration Tests Runner                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Using: $COMPOSE_CMD${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up services...${NC}"
    $COMPOSE_CMD -f $COMPOSE_FILE down -v 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup EXIT INT TERM

# Start services
echo -e "${YELLOW}🚀 Starting services (Neo4j, Redis, NATS)...${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check Neo4j
echo -n "  Checking Neo4j... "
for i in {1..30}; do
    if $COMPOSE_CMD -f $COMPOSE_FILE exec -T neo4j cypher-shell -u neo4j -p testpassword "RETURN 1" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
        exit 1
    fi
    sleep 1
done

# Check Redis
echo -n "  Checking Redis... "
for i in {1..30}; do
    if $COMPOSE_CMD -f $COMPOSE_FILE exec -T redis redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
        exit 1
    fi
    sleep 1
done

# Check NATS
echo -n "  Checking NATS... "
for i in {1..30}; do
    if curl -sf http://localhost:8222/healthz &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}✅ All services ready!${NC}"
echo ""

# Run integration tests
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Running Integration Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Set environment variables for tests
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="testpassword"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export NATS_URL="nats://localhost:4222"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run tests
pytest tests/integration -m integration --tb=short -v

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
fi

exit $TEST_EXIT_CODE

