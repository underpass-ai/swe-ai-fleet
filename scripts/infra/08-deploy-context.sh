#!/usr/bin/env bash
set -euo pipefail

# Context Service Deployment Script
# Deploys Context Service to Kubernetes with validation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
K8S_DIR="$REPO_ROOT/deploy/k8s"
NAMESPACE="swe-ai-fleet"
SERVICE_NAME="context"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       🚀 Deploy Step 8: Context Service                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Pre-checks
echo -e "${YELLOW}🔍 Pre-deployment checks...${NC}"

if [ ! -f "$K8S_DIR/08-context-service.yaml" ]; then
    echo -e "${RED}✗ Manifest not found: $K8S_DIR/08-context-service.yaml${NC}"
    exit 1
fi

if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    echo -e "${RED}✗ Namespace $NAMESPACE does not exist${NC}"
    exit 1
fi

# Check Neo4j dependency
if ! kubectl get service neo4j -n "$NAMESPACE" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Neo4j service not found in namespace $NAMESPACE${NC}"
    echo -e "${YELLOW}   Context Service requires Neo4j to be deployed first${NC}"
fi

# Check Redis dependency
if ! kubectl get service redis -n "$NAMESPACE" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Redis service not found in namespace $NAMESPACE${NC}"
    echo -e "${YELLOW}   Context Service requires Redis to be deployed first${NC}"
fi

echo -e "${GREEN}✓ Pre-checks passed${NC}"
echo ""

# Dry-run
echo -e "${YELLOW}🔍 Dry-run validation...${NC}"
if kubectl apply -f "$K8S_DIR/08-context-service.yaml" --dry-run=client >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Manifest is valid${NC}"
else
    echo -e "${RED}✗ Manifest validation failed${NC}"
    kubectl apply -f "$K8S_DIR/08-context-service.yaml" --dry-run=client
    exit 1
fi
echo ""

# Show what will be deployed
echo -e "${YELLOW}📦 Resources to deploy:${NC}"
kubectl apply -f "$K8S_DIR/08-context-service.yaml" --dry-run=client -o yaml | grep -E "^(kind|  name):" | sed 's/^/  /'
echo ""

# Confirmation prompt
read -p "Deploy Context Service? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  Deployment cancelled${NC}"
    exit 0
fi

# Deploy
echo ""
echo -e "${BLUE}🚀 Deploying Context Service...${NC}"
kubectl apply -f "$K8S_DIR/08-context-service.yaml"
echo ""

# Wait for deployment
echo -e "${YELLOW}⏳ Waiting for Context Service to be ready...${NC}"
kubectl rollout status deployment/context -n "$NAMESPACE" --timeout=300s

# Verify deployment
echo ""
echo -e "${YELLOW}🔍 Verifying deployment...${NC}"

DESIRED=$(kubectl get deployment context -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
READY=$(kubectl get deployment context -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')

if [ "$READY" = "$DESIRED" ]; then
    echo -e "${GREEN}✓ Context Service is running ($READY/$DESIRED replicas)${NC}"
else
    echo -e "${RED}✗ Context Service is not fully ready ($READY/$DESIRED replicas)${NC}"
    exit 1
fi

# Check service
if kubectl get service context -n "$NAMESPACE" >/dev/null 2>&1; then
    SVC_IP=$(kubectl get service context -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    echo -e "${GREEN}✓ Service context is available at $SVC_IP:50054${NC}"
fi

# Show pod status
echo ""
echo -e "${YELLOW}📊 Pod Status:${NC}"
kubectl get pods -n "$NAMESPACE" -l app=context

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          ✅ CONTEXT SERVICE DEPLOYED!                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📝 Next Steps:${NC}"
echo "  • Test gRPC endpoint:"
echo "    grpcurl -plaintext -d '{\"story_id\": \"test\", \"role\": \"DEV\", \"phase\": \"BUILD\"}' \\"
echo "      internal-context:50054 fleet.context.v1.ContextService/GetContext"
echo ""
echo "  • View logs:"
echo "    kubectl logs -n $NAMESPACE -l app=context --tail=50 -f"
echo ""
echo "  • Check service:"
echo "    kubectl get all -n $NAMESPACE -l app=context"
echo ""
echo -e "${YELLOW}⚠️  Rollback:${NC}"
echo "  kubectl delete -f $K8S_DIR/08-context-service.yaml"
echo ""

