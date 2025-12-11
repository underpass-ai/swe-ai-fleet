#!/bin/bash
#
# Cluster Restoration Script
#
# This script restores the Kubernetes cluster by:
# 1. Creating missing secrets (neo4j-auth, huggingface-token if needed)
# 2. Executing a full fresh redeploy
#
# Usage:
#   ./restore-cluster.sh                    # Use default credentials
#   ./restore-cluster.sh --neo4j-user USER --neo4j-password PASS  # Custom Neo4j credentials
#   ./restore-cluster.sh --reset-nats        # Also reset NATS streams

set -euo pipefail

PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# Default credentials (can be overridden)
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-underpassai}"
RESET_NATS=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
step() { echo -e "${BLUE}▶${NC} $1"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --neo4j-user)
            NEO4J_USER="$2"
            shift 2
            ;;
        --neo4j-password)
            NEO4J_PASSWORD="$2"
            shift 2
            ;;
        --reset-nats)
            RESET_NATS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --neo4j-user USER      Neo4j username (default: neo4j)"
            echo "  --neo4j-password PASS  Neo4j password (default: underpassai)"
            echo "  --reset-nats          Also reset NATS streams (clean slate)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  NEO4J_USER            Neo4j username"
            echo "  NEO4J_PASSWORD        Neo4j password"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SWE AI Fleet - Cluster Restoration"
echo "════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# STEP 1: Verify Namespace Exists
# ============================================================================

step "STEP 1: Verifying namespace..."

if ! kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
    warn "Namespace ${NAMESPACE} does not exist, creating it..."
    kubectl create namespace "${NAMESPACE}" || fatal "Failed to create namespace"
    success "Namespace created"
else
    success "Namespace exists"
fi

echo ""

# ============================================================================
# STEP 2: Create Missing Secrets
# ============================================================================

step "STEP 2: Creating missing secrets..."
echo ""

# Check if neo4j-auth secret exists
if kubectl get secret neo4j-auth -n "${NAMESPACE}" >/dev/null 2>&1; then
    info "Secret 'neo4j-auth' already exists"
    info "Recreating it with new credentials..."
    kubectl delete secret neo4j-auth -n "${NAMESPACE}" || true
    sleep 2
fi

info "Creating neo4j-auth secret with user: ${NEO4J_USER}"
kubectl create secret generic neo4j-auth \
    --from-literal=NEO4J_AUTH="${NEO4J_USER}/${NEO4J_PASSWORD}" \
    --from-literal=NEO4J_USER="${NEO4J_USER}" \
    --from-literal=NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
    -n "${NAMESPACE}" && \
    success "neo4j-auth secret created" || \
    error "Failed to create neo4j-auth secret"

# Check if huggingface-token secret exists (optional, only needed for vLLM)
if kubectl get secret huggingface-token -n "${NAMESPACE}" >/dev/null 2>&1; then
    info "Secret 'huggingface-token' already exists"
else
    warn "Secret 'huggingface-token' not found (optional, only needed for vLLM server)"
    warn "If you need vLLM, create it manually with:"
    warn "  kubectl create secret generic huggingface-token --from-literal=HF_TOKEN='your-token' -n ${NAMESPACE}"
fi

echo ""

# ============================================================================
# STEP 3: Apply Foundation Resources
# ============================================================================

step "STEP 3: Applying foundation resources (ConfigMaps, etc.)..."
echo ""

info "Applying ConfigMaps..."
kubectl apply -f "${PROJECT_ROOT}/deploy/k8s/00-foundation/00-configmaps.yaml" && \
    success "ConfigMaps applied" || \
    warn "ConfigMaps apply failed (may already exist)"

echo ""

# ============================================================================
# STEP 4: Execute Fresh Redeploy
# ============================================================================

step "STEP 4: Executing fresh redeploy..."
echo ""

REDEPLOY_CMD="./scripts/infra/fresh-redeploy-v2.sh"
if [ "$RESET_NATS" = true ]; then
    REDEPLOY_CMD="${REDEPLOY_CMD} --reset-nats"
fi

info "Running: ${REDEPLOY_CMD}"
cd "${PROJECT_ROOT}/scripts/infra"

if bash fresh-redeploy-v2.sh ${RESET_NATS:+--reset-nats}; then
    success "Fresh redeploy completed"
else
    error "Fresh redeploy failed - check logs above"
    exit 1
fi

echo ""

# ============================================================================
# STEP 5: Verify Cluster Health
# ============================================================================

step "STEP 5: Verifying cluster health..."
echo ""

cd "${PROJECT_ROOT}/scripts/infra"

if [ -f "verify-health.sh" ]; then
    info "Running health verification..."
    bash verify-health.sh || warn "Health verification reported issues"
else
    warn "verify-health.sh not found, skipping automated health check"
    info "Manual verification: kubectl get pods -n ${NAMESPACE}"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ Cluster Restoration Complete!"
echo "════════════════════════════════════════════════════════"
echo ""

success "Cluster has been restored. Check pod status with:"
info "  kubectl get pods -n ${NAMESPACE}"
info "  kubectl get all -n ${NAMESPACE}"
echo ""





