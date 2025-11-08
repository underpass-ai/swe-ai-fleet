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

# Removed 'set -e' to prevent script from exiting on first error
# This could leave services scaled to 0 if build/push fails
# Instead, we handle errors gracefully with || warn/error

PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
REGISTRY="registry.underpassai.com/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# Base version tags (semantic versioning - will be incremented with timestamp on each build)
ORCHESTRATOR_BASE_TAG="v3.0.0"
RAY_EXECUTOR_BASE_TAG="v3.0.0"
CONTEXT_BASE_TAG="v2.0.0"
MONITORING_BASE_TAG="v3.2.1"
PLANNING_BASE_TAG="v2.0.0"
WORKFLOW_BASE_TAG="v1.0.0"

# Generate version tags with timestamp suffix for uniqueness
# Format: {base-tag}-{YYYYMMDD-HHMMSS}
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
ORCHESTRATOR_TAG="${ORCHESTRATOR_BASE_TAG}-${BUILD_TIMESTAMP}"
RAY_EXECUTOR_TAG="${RAY_EXECUTOR_BASE_TAG}-${BUILD_TIMESTAMP}"
CONTEXT_TAG="${CONTEXT_BASE_TAG}-${BUILD_TIMESTAMP}"
MONITORING_TAG="${MONITORING_BASE_TAG}-${BUILD_TIMESTAMP}"
PLANNING_TAG="${PLANNING_BASE_TAG}-${BUILD_TIMESTAMP}"
WORKFLOW_TAG="${WORKFLOW_BASE_TAG}-${BUILD_TIMESTAMP}"

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
error() { echo -e "${RED}✗${NC} $1"; }  # Removed exit 1 - let caller decide
fatal() { echo -e "${RED}✗ FATAL:${NC} $1"; exit 1; }  # For truly fatal errors
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

NATS_SERVICES=("orchestrator" "context" "monitoring-dashboard" "planning" "workflow")

# Map service names to their YAML deployment files
declare -A SERVICE_YAML
SERVICE_YAML["orchestrator"]="deploy/k8s/11-orchestrator-service.yaml"
SERVICE_YAML["context"]="deploy/k8s/08-context-service.yaml"
SERVICE_YAML["monitoring-dashboard"]="deploy/k8s/13-monitoring-dashboard.yaml"
SERVICE_YAML["planning"]="deploy/k8s/07-planning-service.yaml"  # Fixed: was 06
SERVICE_YAML["workflow"]="deploy/k8s/15-workflow-service.yaml"
SERVICE_YAML["ray-executor"]="deploy/k8s/10-ray-executor-service.yaml"  # Added for consistency

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
# STEP 2: Apply ConfigMaps and Secrets
# ============================================================================

step "STEP 2: Applying ConfigMaps and Secrets..."
echo ""

info "Applying ConfigMaps..."
kubectl apply -f ${PROJECT_ROOT}/deploy/k8s/00-configmaps.yaml && success "ConfigMaps applied" || warn "ConfigMaps failed"

info "Applying Secrets..."
kubectl apply -f ${PROJECT_ROOT}/deploy/k8s/01-secrets.yaml 2>/dev/null && success "Secrets applied" || warn "Secrets not found or already exist"

echo ""

# ============================================================================
# STEP 3: Reset NATS Streams (Optional)
# ============================================================================

if [ "$RESET_NATS" = true ]; then
    step "STEP 3: Resetting NATS streams..."

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
# STEP 4: Build and Push Images (or Skip)
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    step "STEP 4: Building and pushing images..."
    echo ""
    info "Build timestamp: ${BUILD_TIMESTAMP}"
    info "Orchestrator: ${ORCHESTRATOR_TAG}"
    info "Ray-executor: ${RAY_EXECUTOR_TAG}"
    info "Context: ${CONTEXT_TAG}"
    info "Monitoring: ${MONITORING_TAG}"
    info "Planning: ${PLANNING_TAG}"
    info "Workflow: ${WORKFLOW_TAG}"
    echo ""

    # Use existing rebuild-and-deploy script logic
    # Build images (show warnings, fail gracefully)
    info "Building orchestrator..."
    if podman build -q -t ${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} -f services/orchestrator/Dockerfile .; then
        success "Orchestrator built"
    else
        error "Failed to build orchestrator"; BUILD_FAILED=true
    fi

    info "Building ray-executor..."
    if podman build -q -t ${REGISTRY}/ray_executor:${RAY_EXECUTOR_TAG} -f services/ray_executor/Dockerfile .; then
        success "Ray-executor built"
    else
        error "Failed to build ray-executor"; BUILD_FAILED=true
    fi

    info "Building context service..."
    if podman build -q -t ${REGISTRY}/context:${CONTEXT_TAG} -f services/context/Dockerfile .; then
        success "Context built"
    else
        error "Failed to build context"; BUILD_FAILED=true
    fi

    info "Building monitoring dashboard..."
    if podman build -q -t ${REGISTRY}/monitoring:${MONITORING_TAG} -f services/monitoring/Dockerfile .; then
        success "Monitoring built"
    else
        error "Failed to build monitoring"; BUILD_FAILED=true
    fi

    info "Building planning service..."
    if podman build -q -t ${REGISTRY}/planning:${PLANNING_TAG} -f services/planning/Dockerfile .; then
        success "Planning built"
    else
        error "Failed to build planning"; BUILD_FAILED=true
    fi

    info "Building workflow service..."
    if podman build -q -t ${REGISTRY}/workflow:${WORKFLOW_TAG} -f services/workflow/Dockerfile .; then
        success "Workflow built"
    else
        error "Failed to build workflow"; BUILD_FAILED=true
    fi

    # Stop if any builds failed
    if [ "${BUILD_FAILED}" = true ]; then
        fatal "One or more builds failed. Aborting to prevent deploying broken images."
    fi

    echo ""
    step "Pushing images to registry..."

    IMAGES=(
        "${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG}"
        "${REGISTRY}/ray_executor:${RAY_EXECUTOR_TAG}"
        "${REGISTRY}/context:${CONTEXT_TAG}"
        "${REGISTRY}/monitoring:${MONITORING_TAG}"
        "${REGISTRY}/planning:${PLANNING_TAG}"
        "${REGISTRY}/workflow:${WORKFLOW_TAG}"
    )

    # Push images (don't hide errors, fail gracefully)
    PUSH_FAILED=false
    for image in "${IMAGES[@]}"; do
        name=$(echo $image | cut -d'/' -f3 | cut -d':' -f1)
        info "Pushing ${name}..."
        if podman push "$image" 2>&1 | grep -q "Writing manifest"; then
            success "${name} pushed"
        else
            error "Failed to push ${name}"
            PUSH_FAILED=true
        fi
    done

    # Stop if any pushes failed
    if [ "${PUSH_FAILED}" = true ]; then
        fatal "One or more pushes failed. Aborting to prevent deploying unavailable images."
    fi

    echo ""
else
    warn "Skipping build step (--skip-build flag)"
    echo ""
fi

# ============================================================================
# STEP 5: Update Deployments
# ============================================================================

step "STEP 5: Updating Kubernetes deployments..."
echo ""

# Helper function to update or create deployment
update_deployment() {
    local name=$1
    local container=$2
    local image=$3
    local yaml_file=$4
    
    if kubectl get deployment/${name} -n ${NAMESPACE} >/dev/null 2>&1; then
        # Deployment exists - update image
        kubectl set image deployment/${name} \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${name} updated" || warn "Failed to update ${name}"
    else
        # Deployment doesn't exist - apply YAML first, then update image
        info "${name} deployment not found, creating from ${yaml_file}..."
        kubectl apply -f ${PROJECT_ROOT}/${yaml_file} && \
        kubectl set image deployment/${name} \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${name} created and updated" || warn "Failed to create ${name}"
    fi
}

info "Updating orchestrator..."
update_deployment "orchestrator" "orchestrator" "${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG}" "${SERVICE_YAML["orchestrator"]}"

info "Updating ray-executor..."
update_deployment "ray-executor" "ray-executor" "${REGISTRY}/ray_executor:${RAY_EXECUTOR_TAG}" "${SERVICE_YAML["ray-executor"]}"

info "Updating context..."
update_deployment "context" "context" "${REGISTRY}/context:${CONTEXT_TAG}" "${SERVICE_YAML["context"]}"

info "Updating planning..."
update_deployment "planning" "planning" "${REGISTRY}/planning:${PLANNING_TAG}" "${SERVICE_YAML["planning"]}"

info "Updating workflow..."
update_deployment "workflow" "workflow" "${REGISTRY}/workflow:${WORKFLOW_TAG}" "${SERVICE_YAML["workflow"]}"

info "Updating monitoring dashboard..."
update_deployment "monitoring-dashboard" "monitoring" "${REGISTRY}/monitoring:${MONITORING_TAG}" "${SERVICE_YAML["monitoring-dashboard"]}"

echo ""

# ============================================================================
# STEP 6: Scale Services Back Up
# ============================================================================

step "STEP 6: Scaling services back up..."
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
# STEP 7: Verify Deployment
# ============================================================================

step "STEP 7: Verifying deployment health..."
echo ""

DEPLOYMENTS=("orchestrator" "ray-executor" "context" "planning" "workflow" "monitoring-dashboard")

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
    -l 'app in (orchestrator,ray-executor,context,planning,workflow,monitoring-dashboard)' \
    --field-selector=status.phase=Running 2>/dev/null | head -10

echo ""

# Check for crash loops
CRASH_LOOPS=$(kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,planning,workflow,monitoring-dashboard)' \
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

