#!/bin/bash
#
# Deploy SWE AI Fleet - Organized Structure
#
# This script deploys the complete SWE AI Fleet using the reorganized
# directory structure (deploy/k8s/ with subdirectories).
#
# Usage:
#   ./deploy-organized.sh           # Full deploy
#   ./deploy-organized.sh --verify  # Only verify, don't apply

set -e

PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"
K8S_BASE="${PROJECT_ROOT}/deploy/k8s"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VERIFY_ONLY=false

# Parse arguments
if [[ "$1" == "--verify" ]]; then
    VERIFY_ONLY=true
fi

info() { echo -e "${GREEN}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
success() { echo -e "${GREEN}✓${NC} $1"; }
step() { echo -e "${BLUE}▶${NC} $1"; }

cd "$PROJECT_ROOT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SWE AI Fleet - Organized Structure Deploy"
echo "════════════════════════════════════════════════════════"
echo ""

if [ "$VERIFY_ONLY" = true ]; then
    warn "VERIFY MODE - No changes will be applied"
    echo ""
fi

# ============================================================================
# STEP 0: Pre-flight Checks
# ============================================================================

step "STEP 0: Pre-flight checks..."
echo ""

# Check kubectl context
CONTEXT=$(kubectl config current-context)
info "kubectl context: ${CONTEXT}"

# Check namespace exists
if kubectl get namespace ${NAMESPACE} >/dev/null 2>&1; then
    success "Namespace ${NAMESPACE} exists"
else
    warn "Namespace ${NAMESPACE} does not exist - will be created"
fi

# Verify directory structure
REQUIRED_DIRS=(
    "00-foundation"
    "10-infrastructure"
    "20-streams"
    "30-microservices"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "${K8S_BASE}/${dir}" ]; then
        success "${dir}/ exists"
    else
        error "${dir}/ not found - run migration first"
    fi
done

echo ""

if [ "$VERIFY_ONLY" = true ]; then
    success "Pre-flight checks passed"
    exit 0
fi

# ============================================================================
# STEP 1: Foundation
# ============================================================================

step "STEP 1: Deploying foundation..."
echo ""

info "Applying namespace..."
kubectl apply -f ${K8S_BASE}/00-foundation/00-namespace.yaml

info "Applying ConfigMaps..."
kubectl apply -f ${K8S_BASE}/00-foundation/00-configmaps.yaml

info "Applying Secrets..."
if [ -f "${K8S_BASE}/01-secrets.yaml" ]; then
    kubectl apply -f ${K8S_BASE}/01-secrets.yaml && success "Secrets applied"
else
    warn "Secrets file not found - using existing secrets"
fi

success "Foundation deployed"
echo ""

# ============================================================================
# STEP 2: Infrastructure
# ============================================================================

step "STEP 2: Deploying infrastructure..."
echo ""

info "Deploying NATS..."
kubectl apply -f ${K8S_BASE}/10-infrastructure/nats.yaml
kubectl apply -f ${K8S_BASE}/10-infrastructure/nats-internal-dns.yaml

info "Deploying Neo4j..."
kubectl apply -f ${K8S_BASE}/10-infrastructure/neo4j.yaml

info "Deploying Valkey..."
kubectl apply -f ${K8S_BASE}/10-infrastructure/valkey.yaml

info "Deploying Container Registry..."
kubectl apply -f ${K8S_BASE}/10-infrastructure/container-registry.yaml

echo ""
info "Waiting for infrastructure to be ready..."
kubectl wait --for=condition=ready pod -l app=nats -n ${NAMESPACE} --timeout=120s || warn "NATS timeout"
kubectl wait --for=condition=ready pod -l app=neo4j -n ${NAMESPACE} --timeout=120s || warn "Neo4j timeout"
kubectl wait --for=condition=ready pod -l app=valkey -n ${NAMESPACE} --timeout=120s || warn "Valkey timeout"

success "Infrastructure deployed"
echo ""

# ============================================================================
# STEP 3: NATS Streams
# ============================================================================

step "STEP 3: Initializing NATS streams..."
echo ""

kubectl delete job nats-streams-init -n ${NAMESPACE} 2>/dev/null || true
kubectl apply -f ${K8S_BASE}/20-streams/nats-streams-init.yaml
kubectl wait --for=condition=complete job/nats-streams-init -n ${NAMESPACE} --timeout=60s

success "NATS streams initialized"
echo ""

# ============================================================================
# STEP 4: Microservices
# ============================================================================

step "STEP 4: Deploying microservices..."
echo ""

SERVICES=("context" "orchestrator" "planning" "workflow" "ray-executor" "vllm-server")

for service in "${SERVICES[@]}"; do
    info "Deploying ${service}..."
    kubectl apply -f ${K8S_BASE}/30-microservices/${service}.yaml
done

echo ""
info "Waiting for microservices rollouts..."

for service in "${SERVICES[@]}"; do
    info "Waiting for ${service}..."
    kubectl rollout status deployment/${service} -n ${NAMESPACE} --timeout=120s || warn "${service} timeout"
done

success "Microservices deployed"
echo ""

# ============================================================================
# STEP 5: Monitoring (Optional)
# ============================================================================

step "STEP 5: Deploying monitoring stack..."
echo ""

kubectl apply -f ${K8S_BASE}/40-monitoring/monitoring-dashboard.yaml
kubectl apply -f ${K8S_BASE}/40-monitoring/grafana.yaml
kubectl apply -f ${K8S_BASE}/40-monitoring/loki.yaml

success "Monitoring deployed"
echo ""

# ============================================================================
# STEP 6: Ingress (Optional)
# ============================================================================

step "STEP 6: Deploying ingress resources..."
echo ""

kubectl apply -f ${K8S_BASE}/50-ingress/ 2>/dev/null || warn "No ingress files or already applied"

success "Ingress deployed"
echo ""

# ============================================================================
# STEP 7: Verification
# ============================================================================

step "STEP 7: Final verification..."
echo ""

kubectl get pods -n ${NAMESPACE} \
  -l 'app in (orchestrator,context,planning,workflow,ray-executor,vllm-server,monitoring-dashboard)' \
  -o wide

echo ""

RUNNING=$(kubectl get pods -n ${NAMESPACE} \
  -l 'app in (orchestrator,context,planning,workflow,ray-executor,vllm-server)' \
  --field-selector=status.phase=Running 2>/dev/null | grep -c Running || true)

EXPECTED=10  # orchestrator(2) + context(2) + planning(2) + workflow(2) + ray-executor(1) + vllm(1)

if [ "$RUNNING" -ge "$EXPECTED" ]; then
    success "All microservices running (${RUNNING}/${EXPECTED})"
else
    warn "Only ${RUNNING}/${EXPECTED} pods running"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ Deploy Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Access:"
echo "  • UI: https://swe-fleet.underpassai.com"
echo "  • Monitoring: https://monitoring-dashboard.underpassai.com"
echo "  • Grafana: https://grafana.underpassai.com"
echo ""
echo "Next: Verify health with ./verify-health.sh"
echo ""

