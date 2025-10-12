#!/usr/bin/env bash
#
# Script para ejecutar test_persistence_integration.py
# Levanta Neo4j y Redis, ejecuta el test localmente

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

COMPOSE_FILE="docker-compose.persistence.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Context Persistence Integration Test    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f $COMPOSE_FILE down -v 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Start services
cd "$SCRIPT_DIR"
echo -e "${YELLOW}🚀 Starting Neo4j and Redis...${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE up -d

# Wait for services
echo -e "${YELLOW}⏳ Waiting for services...${NC}"
sleep 10

# Check Neo4j
echo -n "  Neo4j... "
for i in {1..30}; do
    if $COMPOSE_CMD -f $COMPOSE_FILE exec -T neo4j cypher-shell -u neo4j -p testpassword "RETURN 1" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    [ $i -eq 30 ] && echo -e "${RED}✗${NC}" && exit 1
    sleep 1
done

# Check Redis
echo -n "  Redis... "
for i in {1..30}; do
    if $COMPOSE_CMD -f $COMPOSE_FILE exec -T redis redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    [ $i -eq 30 ] && echo -e "${RED}✗${NC}" && exit 1
    sleep 1
done

echo ""
echo -e "${GREEN}✅ Services ready${NC}"
echo ""

# Set env vars
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="testpassword"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Activate venv
cd /home/tirso/ai/developents/swe-ai-fleet
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run test
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Running test_persistence_integration.py${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

pytest tests/integration/services/context/test_persistence_integration.py -v --tb=short

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Test PASSED${NC}"
else
    echo -e "${RED}❌ Test FAILED${NC}"
fi

exit $TEST_EXIT_CODE

