#!/bin/bash
#
# Fresh Redeploy All Microservices
#
# This script performs a complete fresh redeploy of all microservices:
# 1. Scales down services with NATS consumers (orchestrator, context, monitoring)
# 2. Rebuilds and pushes images (or uses existing)
# 3. Updates Kubernetes deployments
# 4. Scales services back up
# 5. Verifies health
#
# Usage:
#   ./fresh-redeploy.sh                  # Full rebuild and redeploy
#   ./fresh-redeploy.sh --skip-build     # Only redeploy (use existing images)
#   ./fresh-redeploy.sh --reset-nats     # Also reset NATS streams

set -e

PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
REGISTRY="registry.underpassai.com/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# Base version tags (semantic versioning - will be incremented with timestamp on each build)
ORCHESTRATOR_BASE_TAG="v3.0.0"
RAY_EXECUTOR_BASE_TAG="v3.0.0"
CONTEXT_BASE_TAG="v2.0.0"
MONITORING_BASE_TAG="v3.2.1"

# Generate version tags with timestamp suffix for uniqueness
# Format: {base-tag}-{YYYYMMDD-HHMMSS}
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
ORCHESTRATOR_TAG="${ORCHESTRATOR_BASE_TAG}-${BUILD_TIMESTAMP}"
RAY_EXECUTOR_TAG="${RAY_EXECUTOR_BASE_TAG}-${BUILD_TIMESTAMP}"
CONTEXT_TAG="${CONTEXT_BASE_TAG}-${BUILD_TIMESTAMP}"
MONITORING_TAG="${MONITORING_BASE_TAG}-${BUILD_TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SKIP_BUILD=false
RESET_NATS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --reset-nats)
            RESET_NATS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-build    Skip building images (only push and deploy)"
            echo "  --reset-nats    Also reset NATS streams (clean slate)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

info() { echo -e "${GREEN}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
success() { echo -e "${GREEN}✓${NC} $1"; }
step() { echo -e "${BLUE}▶${NC} $1"; }

cd "$PROJECT_ROOT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SWE AI Fleet - Fresh Redeploy All Microservices"
echo "════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# STEP 1: Scale Down Services with NATS Consumers (CRITICAL)
# ============================================================================

step "STEP 1: Scaling down services with NATS consumers..."

NATS_SERVICES=("orchestrator" "context" "monitoring-dashboard")

# Map service names to their YAML deployment files
declare -A SERVICE_YAML
SERVICE_YAML["orchestrator"]="deploy/k8s/11-orchestrator-service.yaml"
SERVICE_YAML["context"]="deploy/k8s/08-context-service.yaml"
SERVICE_YAML["monitoring-dashboard"]="deploy/k8s/13-monitoring-dashboard.yaml"

# Capture replica counts from YAML deployment files (source of truth)
declare -A ORIGINAL_REPLICAS
for service in "${NATS_SERVICES[@]}"; do
    YAML_FILE="${PROJECT_ROOT}/${SERVICE_YAML["${service}"]}"
    if [ -f "${YAML_FILE}" ]; then
        # Extract replica count from YAML (look for "replicas:" line, take the number)
        REPLICAS=$(grep -E "^\s+replicas:" "${YAML_FILE}" | head -1 | awk '{print $2}' || echo "1")
        ORIGINAL_REPLICAS["${service}"]=${REPLICAS}
        info "Read replica count for ${service} from ${SERVICE_YAML["${service}"]}: ${REPLICAS}"
    else
        warn "YAML file not found for ${service}: ${YAML_FILE}, defaulting to 1 replica"
        ORIGINAL_REPLICAS["${service}"]=1
    fi
done

# Now scale down
for service in "${NATS_SERVICES[@]}"; do
    info "Scaling down ${service}..."
    kubectl scale deployment/${service} -n ${NAMESPACE} --replicas=0 || true
done

info "Waiting for graceful shutdown..."
sleep 10

# Verify pods are terminated
for service in "${NATS_SERVICES[@]}"; do
    kubectl wait --for=delete pod -l app=${service} -n ${NAMESPACE} --timeout=30s 2>/dev/null || true
done

success "All NATS-dependent services scaled down"
echo ""

# ============================================================================
# STEP 2: Reset NATS Streams (Optional)
# ============================================================================

if [ "$RESET_NATS" = true ]; then
    step "STEP 2: Resetting NATS streams..."

    # Delete existing streams
    kubectl delete job nats-delete-streams -n ${NAMESPACE} 2>/dev/null || true
    kubectl apply -f deploy/k8s/02a-nats-delete-streams.yaml
    kubectl wait --for=condition=complete --timeout=30s job/nats-delete-streams -n ${NAMESPACE}

    # Recreate streams
    kubectl delete job nats-init-streams -n ${NAMESPACE} 2>/dev/null || true
    kubectl apply -f deploy/k8s/15-nats-streams-init.yaml || kubectl apply -f deploy/k8s/02b-nats-init-streams.yaml 2>/dev/null || true
    kubectl wait --for=condition=complete --timeout=30s job/nats-init-streams -n ${NAMESPACE} 2>/dev/null || warn "NATS stream init job not found (may need manual stream creation)"

    success "NATS streams reset"
    echo ""
fi

# ============================================================================
# STEP 3: Build and Push Images (or Skip)
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    step "STEP 3: Building and pushing images..."
    echo ""
    info "Build timestamp: ${BUILD_TIMESTAMP}"
    info "Orchestrator: ${ORCHESTRATOR_TAG}"
    info "Ray-executor: ${RAY_EXECUTOR_TAG}"
    info "Context: ${CONTEXT_TAG}"
    info "Monitoring: ${MONITORING_TAG}"
    echo ""

    # Use existing rebuild-and-deploy script logic
    info "Building orchestrator..."
    podman build -q -t ${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} \
        -f services/orchestrator/Dockerfile . > /dev/null && \
        success "Orchestrator built" || error "Failed to build orchestrator"

    info "Building ray-executor..."
    podman build -q -t ${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG} \
        -f services/ray-executor/Dockerfile . > /dev/null && \
        success "Ray-executor built" || error "Failed to build ray-executor"

    info "Building context service..."
    podman build -q -t ${REGISTRY}/context:${CONTEXT_TAG} \
        -f services/context/Dockerfile . > /dev/null && \
        success "Context built" || error "Failed to build context"

    info "Building monitoring dashboard..."
    podman build -q -t ${REGISTRY}/monitoring:${MONITORING_TAG} \
        -f services/monitoring/Dockerfile . > /dev/null && \
        success "Monitoring built" || error "Failed to build monitoring"

    echo ""
    step "Pushing images to registry..."

    IMAGES=(
        "${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG}"
        "${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG}"
        "${REGISTRY}/context:${CONTEXT_TAG}"
        "${REGISTRY}/monitoring:${MONITORING_TAG}"
    )

    for image in "${IMAGES[@]}"; do
        name=$(echo $image | cut -d'/' -f3 | cut -d':' -f1)
        info "Pushing ${name}..."
        podman push "$image" > /dev/null 2>&1 && success "${name} pushed" || error "Failed to push ${name}"
    done

    echo ""
else
    warn "Skipping build step (--skip-build flag)"
    echo ""
fi

# ============================================================================
# STEP 4: Update Deployments
# ============================================================================

step "STEP 4: Updating Kubernetes deployments..."
echo ""

info "Updating orchestrator..."
kubectl set image deployment/orchestrator \
    orchestrator=${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} \
    -n ${NAMESPACE} && success "Orchestrator updated" || error "Failed to update orchestrator"

info "Updating ray-executor..."
kubectl set image deployment/ray-executor \
    ray-executor=${REGISTRY}/ray-executor:${RAY_EXECUTOR_TAG} \
    -n ${NAMESPACE} && success "Ray-executor updated" || error "Failed to update ray-executor"

info "Updating context..."
kubectl set image deployment/context \
    context=${REGISTRY}/context:${CONTEXT_TAG} \
    -n ${NAMESPACE} && success "Context updated" || error "Failed to update context"

info "Updating monitoring dashboard..."
kubectl set image deployment/monitoring-dashboard \
    monitoring=${REGISTRY}/monitoring:${MONITORING_TAG} \
    -n ${NAMESPACE} && success "Monitoring updated" || error "Failed to update monitoring"

echo ""

# ============================================================================
# STEP 5: Scale Services Back Up
# ============================================================================

step "STEP 5: Scaling services back up..."
echo ""

for service in "${NATS_SERVICES[@]}"; do
    # Use the original replica count we captured earlier
    REPLICAS=${ORIGINAL_REPLICAS["${service}"]:-1}
    info "Scaling up ${service} to ${REPLICAS} replicas..."
    kubectl scale deployment/${service} -n ${NAMESPACE} --replicas=${REPLICAS} && \
        success "${service} scaled to ${REPLICAS}" || warn "Failed to scale ${service}"
done

echo ""
info "Waiting for services to be ready..."
sleep 15

# ============================================================================
# STEP 6: Verify Deployment
# ============================================================================

step "STEP 6: Verifying deployment health..."
echo ""

DEPLOYMENTS=("orchestrator" "ray-executor" "context" "monitoring-dashboard")

for deployment in "${DEPLOYMENTS[@]}"; do
    info "Waiting for ${deployment} rollout..."
    if kubectl rollout status deployment/${deployment} -n ${NAMESPACE} --timeout=30s > /dev/null 2>&1; then
        success "${deployment} is ready"
    else
        warn "${deployment} rollout timed out (check logs)"
    fi
done

echo ""
step "Final status check..."
echo ""

kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
    --field-selector=status.phase=Running 2>/dev/null | head -10

echo ""

# Check for crash loops
CRASH_LOOPS=$(kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,monitoring-dashboard)' \
    --field-selector=status.phase!=Running 2>/dev/null | grep -c CrashLoopBackOff || true)

if [ "$CRASH_LOOPS" -gt 0 ]; then
    error "Found ${CRASH_LOOPS} pods in CrashLoopBackOff state"
else
    success "All pods are running!"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ Fresh Redeploy Complete!"
echo "════════════════════════════════════════════════════════"
echo ""

