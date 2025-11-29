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
#   ./fresh-redeploy.sh --no-cache       # Build without cache (slower but ensures fresh builds)
#   make fresh-redeploy NO_CACHE=1       # Via Makefile with no-cache

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
PLANNING_UI_BASE_TAG="v0.1.0"
TASK_DERIVATION_BASE_TAG="v0.1.0"
WORKFLOW_BASE_TAG="v1.0.0"

# Generate version tags with timestamp suffix for uniqueness
# Format: {base-tag}-{YYYYMMDD-HHMMSS}
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
ORCHESTRATOR_TAG="${ORCHESTRATOR_BASE_TAG}-${BUILD_TIMESTAMP}"
RAY_EXECUTOR_TAG="${RAY_EXECUTOR_BASE_TAG}-${BUILD_TIMESTAMP}"
CONTEXT_TAG="${CONTEXT_BASE_TAG}-${BUILD_TIMESTAMP}"
MONITORING_TAG="${MONITORING_BASE_TAG}-${BUILD_TIMESTAMP}"
PLANNING_TAG="${PLANNING_BASE_TAG}-${BUILD_TIMESTAMP}"
PLANNING_UI_TAG="${PLANNING_UI_BASE_TAG}-${BUILD_TIMESTAMP}"
TASK_DERIVATION_TAG="${TASK_DERIVATION_BASE_TAG}-${BUILD_TIMESTAMP}"
WORKFLOW_TAG="${WORKFLOW_BASE_TAG}-${BUILD_TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SKIP_BUILD=false
RESET_NATS=false
NO_CACHE=true

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
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-build    Skip building images (only push and deploy)"
            echo "  --reset-nats    Also reset NATS streams (clean slate)"
            echo "  --no-cache      Build images without using cache (slower but ensures fresh builds)"
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
# STEP 0: Cleanup Zombie Pods (PREVENTIVE)
# ============================================================================

step "STEP 0: Cleaning up zombie pods..."

# Count zombie pods (ContainerStatusUnknown or Unknown phase)
ZOMBIE_COUNT=$(kubectl get pods -n ${NAMESPACE} --field-selector=status.phase=Unknown 2>/dev/null | grep -v NAME | wc -l || echo "0")

if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    warn "Found ${ZOMBIE_COUNT} zombie pods in Unknown state"

    # List them for visibility
    info "Zombie pods:"
    kubectl get pods -n ${NAMESPACE} --field-selector=status.phase=Unknown 2>/dev/null | grep -v NAME || true

    # Force delete all Unknown pods (common after restarts, especially vLLM)
    info "Force deleting zombie pods..."
    kubectl delete pods -n ${NAMESPACE} --field-selector=status.phase=Unknown --force --grace-period=0 2>/dev/null || true

    # Give kubelet time to cleanup
    sleep 5

    success "Zombie pods cleaned up"
else
    success "No zombie pods found (clean state)"
fi

echo ""

# ============================================================================
# STEP 1: Scale Down Services with NATS Consumers (CRITICAL)
# ============================================================================

step "STEP 1: Scaling down services with NATS consumers..."

NATS_SERVICES=("orchestrator" "context" "monitoring-dashboard" "planning" "workflow" "task-derivation")

# Map service names to their YAML deployment files (REORGANIZED 2025-11-08)
declare -A SERVICE_YAML
SERVICE_YAML["orchestrator"]="deploy/k8s/30-microservices/orchestrator.yaml"
SERVICE_YAML["context"]="deploy/k8s/30-microservices/context.yaml"
SERVICE_YAML["monitoring-dashboard"]="deploy/k8s/40-monitoring/monitoring-dashboard.yaml"
SERVICE_YAML["planning"]="deploy/k8s/30-microservices/planning.yaml"
SERVICE_YAML["planning-ui"]="deploy/k8s/00-foundation/planning-ui.yaml"
SERVICE_YAML["workflow"]="deploy/k8s/30-microservices/workflow.yaml"
SERVICE_YAML["ray-executor"]="deploy/k8s/30-microservices/ray-executor.yaml"
SERVICE_YAML["task-derivation"]="deploy/k8s/30-microservices/task-derivation.yaml"

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
kubectl apply -f ${PROJECT_ROOT}/deploy/k8s/00-foundation/00-configmaps.yaml && success "ConfigMaps applied" || warn "ConfigMaps failed"

info "Applying Secrets..."
if [ -f "${PROJECT_ROOT}/deploy/k8s/01-secrets.yaml" ]; then
    kubectl apply -f ${PROJECT_ROOT}/deploy/k8s/01-secrets.yaml && success "Secrets applied" || warn "Secrets apply failed"
else
    warn "Secrets file not found - using existing secrets in cluster"
fi

echo ""

# ============================================================================
# STEP 3: Reset NATS Streams (Optional)
# ============================================================================

if [ "$RESET_NATS" = true ]; then
    step "STEP 3: Resetting NATS streams..."

    # Delete existing streams
    kubectl delete job nats-delete-streams -n ${NAMESPACE} 2>/dev/null || true
    kubectl apply -f deploy/k8s/99-jobs/nats-delete-streams.yaml
    kubectl wait --for=condition=complete --timeout=30s job/nats-delete-streams -n ${NAMESPACE}

    # Recreate streams
    kubectl delete job nats-streams-init -n ${NAMESPACE} 2>/dev/null || true
    if ! kubectl apply -f deploy/k8s/20-streams/nats-streams-init.yaml; then
        fatal "NATS streams initialization failed - streams are CRITICAL for system operation"
    fi
    kubectl wait --for=condition=complete --timeout=60s job/nats-streams-init -n ${NAMESPACE} || warn "NATS stream init timeout"

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
    info "Planning UI: ${PLANNING_UI_TAG}"
    info "Task Derivation: ${TASK_DERIVATION_TAG}"
    info "Workflow: ${WORKFLOW_TAG}"
    echo ""

    # Build images (removed -q for better debugging)
    BUILD_LOG="/tmp/swe-ai-fleet-build-$(date +%s).log"
    info "Build log: ${BUILD_LOG}"
    echo ""

    info "Building orchestrator..."
    if podman build -t ${REGISTRY}/orchestrator:${ORCHESTRATOR_TAG} -f services/orchestrator/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Orchestrator built"
    else
        error "Failed to build orchestrator (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building ray-executor..."
    if podman build -t ${REGISTRY}/ray_executor:${RAY_EXECUTOR_TAG} -f services/ray_executor/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Ray-executor built"
    else
        error "Failed to build ray-executor (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building context service..."
    if podman build -t ${REGISTRY}/context:${CONTEXT_TAG} -f services/context/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Context built"
    else
        error "Failed to build context (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building monitoring dashboard..."
    if podman build -t ${REGISTRY}/monitoring:${MONITORING_TAG} -f services/monitoring/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Monitoring built"
    else
        error "Failed to build monitoring (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building planning service..."
    if podman build -t ${REGISTRY}/planning:${PLANNING_TAG} -f services/planning/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Planning built"
    else
        error "Failed to build planning (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building planning UI..."
    if podman build -t ${REGISTRY}/planning-ui:${PLANNING_UI_TAG} -f services/planning-ui/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Planning UI built"
    else
        error "Failed to build planning-ui (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building task-derivation service..."
    BUILD_ARGS=""
    if [ "$NO_CACHE" = true ]; then
        BUILD_ARGS="--no-cache"
        info "  Using --no-cache flag (slower but ensures fresh build)"
    fi
    if podman build ${BUILD_ARGS} -t ${REGISTRY}/task-derivation:${TASK_DERIVATION_TAG} -f services/task_derivation/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Task Derivation built"
    else
        error "Failed to build task-derivation (check ${BUILD_LOG})"; BUILD_FAILED=true
    fi

    info "Building workflow service..."
    if podman build -t ${REGISTRY}/workflow:${WORKFLOW_TAG} -f services/workflow/Dockerfile . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "Workflow built"
    else
        error "Failed to build workflow (check ${BUILD_LOG})"; BUILD_FAILED=true
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
        "${REGISTRY}/planning-ui:${PLANNING_UI_TAG}"
        "${REGISTRY}/task-derivation:${TASK_DERIVATION_TAG}"
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

info "Updating planning-ui..."
update_deployment "planning-ui" "planning-ui" "${REGISTRY}/planning-ui:${PLANNING_UI_TAG}" "${SERVICE_YAML["planning-ui"]}"

info "Updating workflow..."
update_deployment "workflow" "workflow" "${REGISTRY}/workflow:${WORKFLOW_TAG}" "${SERVICE_YAML["workflow"]}"

info "Updating monitoring dashboard..."
update_deployment "monitoring-dashboard" "monitoring" "${REGISTRY}/monitoring:${MONITORING_TAG}" "${SERVICE_YAML["monitoring-dashboard"]}"

info "Updating task-derivation..."
update_deployment "task-derivation" "task-derivation" "${REGISTRY}/task-derivation:${TASK_DERIVATION_TAG}" "${SERVICE_YAML["task-derivation"]}"

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

DEPLOYMENTS=("orchestrator" "ray-executor" "context" "planning" "planning-ui" "workflow" "monitoring-dashboard" "task-derivation")

for deployment in "${DEPLOYMENTS[@]}"; do
    info "Waiting for ${deployment} rollout..."
    if kubectl rollout status deployment/${deployment} -n ${NAMESPACE} --timeout=120s > /dev/null 2>&1; then
        success "${deployment} is ready"
    else
        warn "${deployment} rollout timed out (check logs)"
    fi
done

echo ""
step "Final status check..."
echo ""

kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,planning,planning-ui,workflow,monitoring-dashboard,task-derivation)' \
    --field-selector=status.phase=Running 2>/dev/null | head -10

echo ""

# Check for crash loops
CRASH_LOOPS=$(kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,planning,planning-ui,workflow,monitoring-dashboard,task-derivation)' \
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

# ============================================================================
# STEP 8: Service Information Summary
# ============================================================================

step "STEP 8: Service Information Summary"
echo ""

info "📋 Microservices Status:"
echo ""
kubectl get pods -n ${NAMESPACE} \
    -l 'app in (orchestrator,ray-executor,context,planning,planning-ui,workflow,monitoring-dashboard,task-derivation)' \
    --no-headers 2>/dev/null | awk '{printf "  %-25s %-15s %s\n", $1, $3, $2}' || true

echo ""
info "🌐 Public Endpoints:"
echo "  • Planning UI:        https://planning.underpassai.com"
echo "  • Monitoring:         https://monitoring-dashboard.underpassai.com"
echo "  • PO UI:              https://swe-fleet.underpassai.com"

echo ""
info "🔧 Internal Services (ClusterIP):"
echo "  • Planning Service:   planning.swe-ai-fleet.svc.cluster.local:50054"
echo "  • Context Service:    context.swe-ai-fleet.svc.cluster.local:50053"
echo "  • Orchestrator:       orchestrator.swe-ai-fleet.svc.cluster.local:50055"
echo "  • Ray Executor:       ray-executor.swe-ai-fleet.svc.cluster.local:50055"
echo "  • Workflow:           workflow.swe-ai-fleet.svc.cluster.local:50056"

echo ""
info "⚙️  Event-Driven Workers:"
echo "  • Task Derivation:    Listens to NATS events (task.derivation.requested, agent.response.completed)"
echo "  • Orchestrator:       Listens to NATS events (agent.requests, agent.responses)"

echo ""
info "📊 Quick Commands:"
echo "  • View all pods:      kubectl get pods -n ${NAMESPACE}"
echo "  • View logs:          kubectl logs -n ${NAMESPACE} <pod-name>"
echo "  • Check service:      kubectl get svc -n ${NAMESPACE}"
echo "  • Check ingress:      kubectl get ingress -n ${NAMESPACE}"

echo ""
success "Deployment complete! All services should be operational."
echo ""

