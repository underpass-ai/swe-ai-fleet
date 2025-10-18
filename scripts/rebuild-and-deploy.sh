#!/bin/bash
#
# Rebuild and Redeploy All Services
#
# This script rebuilds all Docker images, pushes them to the registry,
# and redeploys them to Kubernetes with verification.
#
# Usage:
#   ./scripts/rebuild-and-deploy.sh
#   ./scripts/rebuild-and-deploy.sh --skip-build   # Only deploy existing images
#   ./scripts/rebuild-and-deploy.sh --no-wait      # Don't wait for rollout

set -e

# Configuration
PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
REGISTRY="registry.underpassai.com/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# Version tags
ORCHESTRATOR_TAG="v2.2.2-api-versioned"
RAY_EXECUTOR_TAG="v2.1.2-api-versioned"
CONTEXT_TAG="v1.1.2-api-versioned"
JOBS_TAG="v1.1.2-api-versioned"
MONITORING_TAG="v1.1.2-deliberations"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
SKIP_BUILD=false
NO_WAIT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --no-wait)
            NO_WAIT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-build    Skip building images (only push and deploy)"
            echo "  --no-wait       Don't wait for rollout completion"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
info() { echo -e "${GREEN}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
success() { echo -e "${GREEN}✓${NC} $1"; }
step() { echo -e "${BLUE}▶${NC} $1"; }

cd "$PROJECT_ROOT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SWE AI Fleet - Rebuild & Redeploy"
echo "════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# STEP 1: Build Docker Images
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    step "STEP 1/4: Building Docker images..."
    echo ""
    
    info "Building orchestrator..."
    if podman build -q -t ${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} \
        -f services/orchestrator/Dockerfile . > /dev/null; then
        success "Orchestrator built (${ORCHESTRATOR_TAG})"
    else
        error "Failed to build orchestrator"
    fi
    
    info "Building ray-executor..."
    if podman build -q -t ${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG} \
        -f services/ray-executor/Dockerfile . > /dev/null; then
        success "Ray-executor built (${RAY_EXECUTOR_TAG})"
    else
        error "Failed to build ray-executor"
    fi
    
    info "Building context service..."
    if podman build -q -t ${REGISTRY}/context:${CONTEXT_TAG} \
        -f services/context/Dockerfile . > /dev/null; then
        success "Context built (${CONTEXT_TAG})"
    else
        error "Failed to build context"
    fi
    
    info "Building orchestrator jobs..."
    if podman build -q -t ${REGISTRY}/orchestrator-jobs:${JOBS_TAG} \
        -f jobs/orchestrator/Dockerfile . > /dev/null; then
        success "Jobs built (${JOBS_TAG})"
    else
        error "Failed to build jobs"
    fi
    
    info "Building monitoring dashboard..."
    if podman build -q -t ${REGISTRY}/monitoring:${MONITORING_TAG} \
        -f services/monitoring/Dockerfile . > /dev/null; then
        success "Monitoring built (${MONITORING_TAG})"
    else
        error "Failed to build monitoring"
    fi
    
    echo ""
    success "All images built successfully!"
    echo ""
else
    warn "Skipping build step (--skip-build flag)"
    echo ""
fi

# ============================================================================
# STEP 2: Push Images to Registry
# ============================================================================

step "STEP 2/4: Pushing images to registry..."
echo ""

IMAGES=(
    "${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG}"
    "${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG}"
    "${REGISTRY}/context:${CONTEXT_TAG}"
    "${REGISTRY}/orchestrator-jobs:${JOBS_TAG}"
    "${REGISTRY}/monitoring:${MONITORING_TAG}"
)

for image in "${IMAGES[@]}"; do
    name=$(echo $image | cut -d'/' -f3 | cut -d':' -f1)
    info "Pushing ${name}..."
    if podman push "$image" 2>&1 | grep -q "Writing manifest"; then
        success "${name} pushed"
    else
        error "Failed to push ${name}"
    fi
done

echo ""
success "All images pushed successfully!"
echo ""

# ============================================================================
# STEP 3: Deploy to Kubernetes
# ============================================================================

step "STEP 3/4: Deploying to Kubernetes..."
echo ""

info "Updating orchestrator deployment..."
kubectl set image deployment/orchestrator \
    orchestrator=${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} \
    -n ${NAMESPACE} || error "Failed to update orchestrator"
success "Orchestrator deployment updated"

info "Updating ray-executor deployment..."
kubectl set image deployment/ray-executor \
    ray-executor=${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG} \
    -n ${NAMESPACE} || error "Failed to update ray-executor"
success "Ray-executor deployment updated"

info "Updating context deployment..."
kubectl set image deployment/context \
    context=${REGISTRY}/context:${CONTEXT_TAG} \
    -n ${NAMESPACE} || error "Failed to update context"
success "Context deployment updated"

info "Updating monitoring dashboard deployment..."
kubectl set image deployment/monitoring-dashboard \
    monitoring=${REGISTRY}/monitoring:${MONITORING_TAG} \
    -n ${NAMESPACE} || error "Failed to update monitoring"
success "Monitoring deployment updated"

echo ""
success "All deployments updated!"
echo ""

# ============================================================================
# STEP 4: Wait for Rollout and Verify
# ============================================================================

if [ "$NO_WAIT" = false ]; then
    step "STEP 4/4: Waiting for rollout completion..."
    echo ""
    
    DEPLOYMENTS=("orchestrator" "ray-executor" "context" "monitoring-dashboard")
    
    for deployment in "${DEPLOYMENTS[@]}"; do
        info "Waiting for ${deployment} rollout..."
        if kubectl rollout status deployment/${deployment} \
            -n ${NAMESPACE} --timeout=120s > /dev/null 2>&1; then
            success "${deployment} rolled out successfully"
        else
            warn "${deployment} rollout timed out or failed (check logs)"
        fi
    done
    
    echo ""
    step "Verifying pod status..."
    echo ""
    
    # Wait a bit for pods to stabilize
    sleep 10
    
    # Get pod status
    kubectl get pods -n ${NAMESPACE} \
        -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
        --field-selector=status.phase=Running \
        2>/dev/null | head -10
    
    echo ""
    
    # Check for crash loops
    CRASH_LOOPS=$(kubectl get pods -n ${NAMESPACE} \
        -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
        --field-selector=status.phase!=Running 2>/dev/null | grep -c CrashLoopBackOff || true)
    
    if [ "$CRASH_LOOPS" -gt 0 ]; then
        warn "Found ${CRASH_LOOPS} pods in CrashLoopBackOff state"
        echo ""
        echo "Pods with issues:"
        kubectl get pods -n ${NAMESPACE} \
            -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
            | grep -E "CrashLoopBackOff|Error|Pending" || true
        echo ""
        warn "Check logs with: kubectl logs -n ${NAMESPACE} <pod-name>"
    else
        success "All pods are running without crash loops!"
    fi
    
    echo ""
    
    # Check readiness
    info "Checking service readiness..."
    TOTAL_RUNNING=$(kubectl get pods -n ${NAMESPACE} \
        -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
        --field-selector=status.phase=Running \
        --no-headers 2>/dev/null | wc -l || echo "0")
    
    READY_COUNT=$(kubectl get pods -n ${NAMESPACE} \
        -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
        -o jsonpath='{.items[?(@.status.phase=="Running")].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | \
        grep -o "True" | wc -l || echo "0")
    
    echo ""
    info "Ready pods: ${READY_COUNT}/${TOTAL_RUNNING}"
    
    if [ "$READY_COUNT" -ge 4 ]; then
        success "Sufficient pods are ready!"
    else
        warn "Some pods may not be ready yet (give them a moment)"
    fi
    
else
    warn "Skipping rollout verification (--no-wait flag)"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ Rebuild & Redeploy Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
info "Next steps:"
echo "  1. Check logs: kubectl logs -n ${NAMESPACE} deployment/<name>"
echo "  2. Monitor pods: kubectl get pods -n ${NAMESPACE} -w"
echo "  3. Test deliberation: Run test case from monitoring dashboard"
echo "  4. Dashboard URL: http://monitoring.underpassai.com"
echo ""

