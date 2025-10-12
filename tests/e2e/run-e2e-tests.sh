#!/usr/bin/env bash
#
# Script para ejecutar tests E2E contra el cluster Kubernetes real
#
# Este script:
# 1. Verifica acceso al cluster
# 2. Hace port-forward al Orchestrator
# 3. Ejecuta tests E2E
# 4. Limpia port-forward

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  E2E Tests - Kubernetes Cluster          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found${NC}"
    exit 1
fi

# Check cluster access
echo -e "${YELLOW}🔍 Checking cluster access...${NC}"
if ! kubectl get ns swe-ai-fleet &>/dev/null; then
    echo -e "${RED}❌ Cannot access namespace swe-ai-fleet${NC}"
    echo -e "${YELLOW}   Check your KUBECONFIG${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Cluster accessible${NC}"

# Check if Orchestrator is running
echo -e "${YELLOW}🔍 Checking Orchestrator service...${NC}"
if ! kubectl get svc -n swe-ai-fleet orchestrator &>/dev/null; then
    echo -e "${RED}❌ Orchestrator service not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Orchestrator service found${NC}"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up port-forward...${NC}"
    pkill -f "kubectl port-forward.*orchestrator" 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup EXIT INT TERM

# Start port-forward
echo -e "${YELLOW}🔌 Starting port-forward to Orchestrator...${NC}"
kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055 &>/dev/null &
PORT_FORWARD_PID=$!

# Wait for port-forward to be ready
sleep 3

# Verify port-forward is working
if ! nc -z localhost 50055 2>/dev/null; then
    echo -e "${RED}❌ Port-forward failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Port-forward ready (localhost:50055)${NC}"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run E2E tests
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Running E2E Tests Against Cluster${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Set environment variables
export ORCHESTRATOR_HOST="localhost"
export ORCHESTRATOR_PORT="50055"

# Run tests
pytest tests/e2e -m e2e --tb=short -v

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ E2E tests PASSED${NC}"
else
    echo -e "${RED}❌ E2E tests FAILED${NC}"
fi

exit $TEST_EXIT_CODE

