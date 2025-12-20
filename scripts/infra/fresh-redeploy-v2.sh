#!/bin/bash
#
# Fresh Redeploy Microservices - Enhanced Version (v2)
#
# This script performs a fresh redeploy of microservices with improved UX:
# - Deploy individual services or all services
# - Fast deploy (with cache) or fresh deploy (no cache)
# - Better error handling and user feedback
#
# Usage:
#   ./fresh-redeploy-v2.sh                          # Deploy all services (fresh, no cache)
#   ./fresh-redeploy-v2.sh --service planning       # Deploy only planning service (fresh)
#   ./fresh-redeploy-v2.sh --service planning --fast # Deploy planning with cache (faster)
#   ./fresh-redeploy-v2.sh --service planning --fresh # Deploy planning without cache (explicit)
#   ./fresh-redeploy-v2.sh --list-services          # List all available services
#   ./fresh-redeploy-v2.sh --skip-build             # Skip build, only redeploy
#   ./fresh-redeploy-v2.sh --reset-nats             # Also reset NATS streams
#
# Examples:
#   make deploy-service SERVICE=planning FAST=1     # Fast deploy via Makefile
#   make deploy-service SERVICE=planning             # Fresh deploy via Makefile

PROJECT_ROOT="/home/tirso/ai/developents/swe-ai-fleet"
REGISTRY="registry.underpassai.com/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# ============================================================================
# Service Configuration
# ============================================================================

# Base version tags (semantic versioning - will be incremented with timestamp on each build)
declare -A SERVICE_BASE_TAGS
SERVICE_BASE_TAGS["orchestrator"]="v3.0.0"
SERVICE_BASE_TAGS["ray-executor"]="v3.0.0"
SERVICE_BASE_TAGS["context"]="v2.0.0"
SERVICE_BASE_TAGS["planning"]="v2.0.0"
SERVICE_BASE_TAGS["planning-ui"]="v0.1.0"
SERVICE_BASE_TAGS["task-derivation"]="v0.1.0"
SERVICE_BASE_TAGS["backlog-review-processor"]="v0.1.0"
SERVICE_BASE_TAGS["workflow"]="v1.0.0"

# Map service names to their Dockerfile paths
declare -A SERVICE_DOCKERFILE
SERVICE_DOCKERFILE["orchestrator"]="services/orchestrator/Dockerfile"
SERVICE_DOCKERFILE["ray-executor"]="services/ray_executor/Dockerfile"
SERVICE_DOCKERFILE["context"]="services/context/Dockerfile"
SERVICE_DOCKERFILE["planning"]="services/planning/Dockerfile"
SERVICE_DOCKERFILE["planning-ui"]="services/planning-ui/Dockerfile"
SERVICE_DOCKERFILE["task-derivation"]="services/task_derivation/Dockerfile"
SERVICE_DOCKERFILE["backlog-review-processor"]="services/backlog_review_processor/Dockerfile"
SERVICE_DOCKERFILE["workflow"]="services/workflow/Dockerfile"

# Map service names to their YAML deployment files
declare -A SERVICE_YAML
SERVICE_YAML["orchestrator"]="deploy/k8s/30-microservices/orchestrator.yaml"
SERVICE_YAML["context"]="deploy/k8s/30-microservices/context.yaml"
SERVICE_YAML["planning"]="deploy/k8s/30-microservices/planning.yaml"
SERVICE_YAML["planning-ui"]="deploy/k8s/00-foundation/planning-ui.yaml"
SERVICE_YAML["workflow"]="deploy/k8s/30-microservices/workflow.yaml"
SERVICE_YAML["ray-executor"]="deploy/k8s/30-microservices/ray-executor.yaml"
SERVICE_YAML["task-derivation"]="deploy/k8s/30-microservices/task-derivation.yaml"
SERVICE_YAML["backlog-review-processor"]="deploy/k8s/30-microservices/backlog-review-processor.yaml"
SERVICE_YAML["vllm-server"]="deploy/k8s/30-microservices/vllm-server.yaml"

# Map service names to container names in deployments (some differ from service name)
declare -A SERVICE_CONTAINER
SERVICE_CONTAINER["orchestrator"]="orchestrator"
SERVICE_CONTAINER["ray-executor"]="ray-executor"
SERVICE_CONTAINER["context"]="context"
SERVICE_CONTAINER["planning"]="planning"
SERVICE_CONTAINER["planning-ui"]="planning-ui"
SERVICE_CONTAINER["task-derivation"]="task-derivation"
SERVICE_CONTAINER["backlog-review-processor"]="backlog-review-processor"
SERVICE_CONTAINER["workflow"]="workflow"

# Map service names to registry image names (some use underscores)
declare -A SERVICE_IMAGE_NAME
SERVICE_IMAGE_NAME["orchestrator"]="orchestrator"
SERVICE_IMAGE_NAME["ray-executor"]="ray-executor"
SERVICE_IMAGE_NAME["context"]="context"
SERVICE_IMAGE_NAME["planning"]="planning"
SERVICE_IMAGE_NAME["planning-ui"]="planning-ui"
SERVICE_IMAGE_NAME["task-derivation"]="task-derivation"
SERVICE_IMAGE_NAME["backlog-review-processor"]="backlog-review-processor"
SERVICE_IMAGE_NAME["workflow"]="workflow"

# Services that have NATS consumers (need graceful shutdown)
declare -A SERVICE_HAS_NATS
SERVICE_HAS_NATS["orchestrator"]=1
SERVICE_HAS_NATS["context"]=1
SERVICE_HAS_NATS["planning"]=1
SERVICE_HAS_NATS["workflow"]=1
SERVICE_HAS_NATS["task-derivation"]=1
SERVICE_HAS_NATS["backlog-review-processor"]=1
SERVICE_HAS_NATS["ray-executor"]=0
SERVICE_HAS_NATS["planning-ui"]=0
SERVICE_HAS_NATS["vllm-server"]=0

# Services that don't need build (use external images)
declare -A SERVICE_NO_BUILD
SERVICE_NO_BUILD["vllm-server"]=1

# All available services
ALL_SERVICES=("orchestrator" "ray-executor" "context" "planning" "planning-ui" "workflow" "task-derivation" "backlog-review-processor" "vllm-server")

# ============================================================================
# Colors and Logging
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

info() { echo -e "${GREEN}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
fatal() { echo -e "${RED}✗ FATAL:${NC} $1"; exit 1; }
success() { echo -e "${GREEN}✓${NC} $1"; }
step() { echo -e "${BLUE}▶${NC} $1"; }
highlight() { echo -e "${CYAN}→${NC} $1"; }

# ============================================================================
# Argument Parsing
# ============================================================================

TARGET_SERVICE=""
SKIP_BUILD=false
RESET_NATS=false
NO_CACHE=true  # Default to fresh (no cache)
LIST_SERVICES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --service|-s)
            TARGET_SERVICE="$2"
            shift 2
            ;;
        --fast)
            NO_CACHE=false
            shift
            ;;
        --fresh)
            NO_CACHE=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --reset-nats)
            RESET_NATS=true
            shift
            ;;
        --list-services|-l)
            LIST_SERVICES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -s, --service <name>    Deploy specific service (default: all services)"
            echo "  --fast                 Use cache for faster builds (default: --fresh)"
            echo "  --fresh                Build without cache (slower but ensures fresh builds)"
            echo "  --skip-build           Skip building images (only redeploy existing images)"
            echo "  --reset-nats           Also reset NATS streams (clean slate)"
            echo "  -l, --list-services    List all available services"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Deploy all services (fresh)"
            echo "  $0 --service planning                 # Deploy planning service (fresh)"
            echo "  $0 --service planning --fast          # Deploy planning with cache"
            echo "  $0 --service planning --skip-build   # Redeploy planning without rebuilding"
            echo ""
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

# ============================================================================
# Helper Functions
# ============================================================================

# Validate service name
validate_service() {
    local service=$1
    for valid_service in "${ALL_SERVICES[@]}"; do
        if [ "$service" = "$valid_service" ]; then
            return 0
        fi
    done
    return 1
}

# List all available services
list_services() {
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "  Available Microservices"
    echo "════════════════════════════════════════════════════════"
    echo ""
    printf "  %-20s %-15s %-15s %s\n" "SERVICE" "HAS NATS" "NEEDS BUILD" "DOCKERFILE/YAML"
    echo "  ─────────────────────────────────────────────────────────────────────"
    for service in "${ALL_SERVICES[@]}"; do
        local has_nats="No"
        if [ "${SERVICE_HAS_NATS[$service]}" = "1" ]; then
            has_nats="Yes"
        fi
        local needs_build="Yes"
        if [ "${SERVICE_NO_BUILD[$service]}" = "1" ]; then
            needs_build="No"
        fi
        local dockerfile_or_yaml="${SERVICE_DOCKERFILE[$service]:-${SERVICE_YAML[$service]}}"
        printf "  %-20s %-15s %-15s %s\n" "$service" "$has_nats" "$needs_build" "$dockerfile_or_yaml"
    done
    echo ""
    echo "Usage examples:"
    echo "  $0 --service planning --fast"
    echo "  $0 --service orchestrator --fresh"
    echo ""
}

# Get services to deploy (single service or all)
get_services_to_deploy() {
    if [ -n "$TARGET_SERVICE" ]; then
        if ! validate_service "$TARGET_SERVICE"; then
            error "Invalid service: $TARGET_SERVICE"
            echo ""
            echo "Valid services:"
            for service in "${ALL_SERVICES[@]}"; do
                echo "  - $service"
            done
            exit 1
        fi
        echo "$TARGET_SERVICE"
    else
        # Return all services
        printf '%s\n' "${ALL_SERVICES[@]}"
    fi
}

# Get replica count from YAML
get_replica_count() {
    local service=$1
    local yaml_file="${PROJECT_ROOT}/${SERVICE_YAML[$service]}"
    if [ -f "$yaml_file" ]; then
        grep -E "^\s+replicas:" "$yaml_file" | head -1 | awk '{print $2}' || echo "1"
    else
        echo "1"
    fi
}

# Build image for a service
build_service_image() {
    local service=$1
    local tag=$2

    # Skip build for services that don't need it (e.g., vllm-server uses external image)
    if [ "${SERVICE_NO_BUILD[$service]}" = "1" ]; then
        info "Skipping build for ${service} (uses external image)"
        return 0
    fi

    local dockerfile="${SERVICE_DOCKERFILE[$service]}"
    local image_name="${SERVICE_IMAGE_NAME[$service]}"
    local image="${REGISTRY}/${image_name}:${tag}"

    if [ ! -f "$dockerfile" ]; then
        error "Dockerfile not found: $dockerfile"
        return 1
    fi

    local build_args=""
    if [ "$NO_CACHE" = true ]; then
        build_args="--no-cache"
        info "Building ${service} (fresh, no cache)..."
    else
        info "Building ${service} (fast, with cache)..."
    fi

    if podman build $build_args -t "$image" -f "$dockerfile" . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "${service} built successfully"
        return 0
    else
        error "Failed to build ${service} (check ${BUILD_LOG})"
        return 1
    fi
}

# Push image to registry
push_service_image() {
    local service=$1
    local tag=$2

    # Skip push for services that don't need build
    if [ "${SERVICE_NO_BUILD[$service]}" = "1" ]; then
        info "Skipping push for ${service} (uses external image)"
        return 0
    fi

    local image_name="${SERVICE_IMAGE_NAME[$service]}"
    local image="${REGISTRY}/${image_name}:${tag}"

    info "Pushing ${service}..."
    if podman push "$image" 2>&1 | grep -q "Writing manifest"; then
        success "${service} pushed successfully"
        return 0
    else
        error "Failed to push ${service}"
        return 1
    fi
}

# Update deployment
update_deployment() {
    local service=$1
    local tag=$2
    local yaml_file="${SERVICE_YAML[$service]}"

    # Services without build (e.g., vllm-server) only need YAML apply
    if [ "${SERVICE_NO_BUILD[$service]}" = "1" ]; then
        info "Applying ${service} deployment (external image, no build needed)..."
        if kubectl apply -f "${PROJECT_ROOT}/${yaml_file}"; then
            success "${service} applied successfully"
            return 0
        else
            error "Failed to apply ${service}"
            return 1
        fi
    fi

    # Services with build need image update
    local container="${SERVICE_CONTAINER[$service]}"
    local image_name="${SERVICE_IMAGE_NAME[$service]}"
    local image="${REGISTRY}/${image_name}:${tag}"

    if kubectl get deployment/"$service" -n ${NAMESPACE} >/dev/null 2>&1; then
        # Deployment exists - update image
        kubectl set image deployment/"$service" \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${service} updated" || warn "Failed to update ${service}"
    else
        # Deployment doesn't exist - apply YAML first, then update image
        info "${service} deployment not found, creating from ${yaml_file}..."
        kubectl apply -f "${PROJECT_ROOT}/${yaml_file}" && \
        kubectl set image deployment/"$service" \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${service} created and updated" || warn "Failed to create ${service}"
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

# Handle list services request
if [ "$LIST_SERVICES" = true ]; then
    list_services
    exit 0
fi

# Get services to deploy
SERVICES_TO_DEPLOY=($(get_services_to_deploy))

# Generate build timestamp
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

# Generate tags for services to deploy
declare -A SERVICE_TAGS
for service in "${SERVICES_TO_DEPLOY[@]}"; do
    base_tag="${SERVICE_BASE_TAGS[$service]}"
    SERVICE_TAGS["$service"]="${base_tag}-${BUILD_TIMESTAMP}"
done

# Display header
echo ""
echo "════════════════════════════════════════════════════════"
if [ -n "$TARGET_SERVICE" ]; then
    echo "  SWE AI Fleet - Deploy Service: ${TARGET_SERVICE}"
else
    echo "  SWE AI Fleet - Deploy All Microservices"
fi
echo "════════════════════════════════════════════════════════"
echo ""

if [ "$NO_CACHE" = true ]; then
    highlight "Mode: Fresh (no cache)"
else
    highlight "Mode: Fast (with cache)"
fi

if [ "$SKIP_BUILD" = true ]; then
    highlight "Build: Skipped (using existing images)"
else
    highlight "Build: Enabled"
fi

echo ""

# ============================================================================
# STEP 0: Cleanup Zombie Pods
# ============================================================================

step "STEP 0: Cleaning up zombie pods..."

ZOMBIE_COUNT=$(kubectl get pods -n ${NAMESPACE} --field-selector=status.phase=Unknown 2>/dev/null | grep -v NAME | wc -l || echo "0")

if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    warn "Found ${ZOMBIE_COUNT} zombie pods in Unknown state"
    info "Force deleting zombie pods..."
    kubectl delete pods -n ${NAMESPACE} --field-selector=status.phase=Unknown --force --grace-period=0 2>/dev/null || true
    sleep 5
    success "Zombie pods cleaned up"
else
    success "No zombie pods found (clean state)"
fi

echo ""

# ============================================================================
# STEP 1: Scale Down Services (only those being deployed)
# ============================================================================

step "STEP 1: Scaling down services..."

# Identify services with NATS that need graceful shutdown
declare -A SERVICES_TO_SCALE_DOWN
declare -A ORIGINAL_REPLICAS

for service in "${SERVICES_TO_DEPLOY[@]}"; do
    if [ "${SERVICE_HAS_NATS[$service]}" = "1" ]; then
        SERVICES_TO_SCALE_DOWN["$service"]=1
        REPLICAS=$(get_replica_count "$service")
        ORIGINAL_REPLICAS["$service"]=$REPLICAS
        info "Will scale down ${service} (currently ${REPLICAS} replicas)"
    fi
done

# Scale down
for service in "${!SERVICES_TO_SCALE_DOWN[@]}"; do
    info "Scaling down ${service}..."
    kubectl scale deployment/"$service" -n ${NAMESPACE} --replicas=0 || true
done

if [ ${#SERVICES_TO_SCALE_DOWN[@]} -gt 0 ]; then
    info "Waiting for graceful shutdown..."
    sleep 10

    # Verify pods are terminated
    for service in "${!SERVICES_TO_SCALE_DOWN[@]}"; do
        kubectl wait --for=delete pod -l app="$service" -n ${NAMESPACE} --timeout=30s 2>/dev/null || true
    done

    success "Services scaled down"
else
    info "No NATS-dependent services to scale down"
fi

echo ""

# ============================================================================
# STEP 2: Apply ConfigMaps and Secrets
# ============================================================================

step "STEP 2: Applying ConfigMaps and Secrets..."

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

    kubectl delete job nats-delete-streams -n ${NAMESPACE} 2>/dev/null || true
    kubectl apply -f deploy/k8s/99-jobs/nats-delete-streams.yaml
    kubectl wait --for=condition=complete --timeout=30s job/nats-delete-streams -n ${NAMESPACE}

    kubectl delete job nats-streams-init -n ${NAMESPACE} 2>/dev/null || true
    if ! kubectl apply -f deploy/k8s/20-streams/nats-streams-init.yaml; then
        fatal "NATS streams initialization failed - streams are CRITICAL for system operation"
    fi
    kubectl wait --for=condition=complete --timeout=60s job/nats-streams-init -n ${NAMESPACE} || warn "NATS stream init timeout"

    success "NATS streams reset"
    echo ""
fi

# ============================================================================
# STEP 4: Build and Push Images
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    step "STEP 4: Building and pushing images..."
    echo ""

    info "Build timestamp: ${BUILD_TIMESTAMP}"
    for service in "${SERVICES_TO_DEPLOY[@]}"; do
        highlight "${service}: ${SERVICE_TAGS[$service]}"
    done
    echo ""

    BUILD_LOG="/tmp/swe-ai-fleet-build-$(date +%s).log"
    info "Build log: ${BUILD_LOG}"
    echo ""

    # Build images
    BUILD_FAILED=false
    for service in "${SERVICES_TO_DEPLOY[@]}"; do
        if ! build_service_image "$service" "${SERVICE_TAGS[$service]}"; then
            BUILD_FAILED=true
        fi
    done

    if [ "$BUILD_FAILED" = true ]; then
        fatal "One or more builds failed. Aborting to prevent deploying broken images."
    fi

    echo ""
    step "Pushing images to registry..."

    # Push images
    PUSH_FAILED=false
    for service in "${SERVICES_TO_DEPLOY[@]}"; do
        if ! push_service_image "$service" "${SERVICE_TAGS[$service]}"; then
            PUSH_FAILED=true
        fi
    done

    if [ "$PUSH_FAILED" = true ]; then
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

for service in "${SERVICES_TO_DEPLOY[@]}"; do
    info "Updating ${service}..."
    update_deployment "$service" "${SERVICE_TAGS[$service]}"
done

echo ""

# ============================================================================
# STEP 6: Scale Services Back Up
# ============================================================================

step "STEP 6: Scaling services back up..."
echo ""

for service in "${!SERVICES_TO_SCALE_DOWN[@]}"; do
    REPLICAS=${ORIGINAL_REPLICAS["$service"]:-1}
    info "Scaling up ${service} to ${REPLICAS} replicas..."
    kubectl scale deployment/"$service" -n ${NAMESPACE} --replicas=${REPLICAS} && \
        success "${service} scaled to ${REPLICAS}" || warn "Failed to scale ${service}"
done

if [ ${#SERVICES_TO_SCALE_DOWN[@]} -gt 0 ]; then
    echo ""
    info "Waiting for services to be ready..."
    sleep 15
fi

# ============================================================================
# STEP 7: Verify Deployment
# ============================================================================

step "STEP 7: Verifying deployment health..."
echo ""

for service in "${SERVICES_TO_DEPLOY[@]}"; do
    info "Waiting for ${service} rollout..."
    if kubectl rollout status deployment/"$service" -n ${NAMESPACE} --timeout=120s > /dev/null 2>&1; then
        success "${service} is ready"
    else
        warn "${service} rollout timed out (check logs: kubectl logs -n ${NAMESPACE} -l app=${service})"
    fi
done

echo ""
step "Final status check..."
echo ""

# Build label selector for services
LABEL_SELECTOR=""
for service in "${SERVICES_TO_DEPLOY[@]}"; do
    if [ -z "$LABEL_SELECTOR" ]; then
        LABEL_SELECTOR="app=${service}"
    else
        LABEL_SELECTOR="${LABEL_SELECTOR},app=${service}"
    fi
done

kubectl get pods -n ${NAMESPACE} \
    -l "$LABEL_SELECTOR" \
    --field-selector=status.phase=Running 2>/dev/null | head -10

echo ""

# Check for crash loops
CRASH_LOOPS=$(kubectl get pods -n ${NAMESPACE} \
    -l "$LABEL_SELECTOR" \
    --field-selector=status.phase!=Running 2>/dev/null | grep -c CrashLoopBackOff || true)

if [ "$CRASH_LOOPS" -gt 0 ]; then
    error "Found ${CRASH_LOOPS} pods in CrashLoopBackOff state"
    echo ""
    info "Troubleshooting:"
    echo "  kubectl get pods -n ${NAMESPACE} -l \"$LABEL_SELECTOR\""
    echo "  kubectl logs -n ${NAMESPACE} <pod-name>"
else
    success "All pods are running!"
fi

echo ""
echo "════════════════════════════════════════════════════════"
if [ -n "$TARGET_SERVICE" ]; then
    echo "  ✓ Service Deploy Complete: ${TARGET_SERVICE}"
else
    echo "  ✓ Fresh Redeploy Complete!"
fi
echo "════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# STEP 8: Service Information Summary
# ============================================================================

step "STEP 8: Service Information Summary"
echo ""

info "📋 Deployed Services Status:"
echo ""
kubectl get pods -n ${NAMESPACE} \
    -l "$LABEL_SELECTOR" \
    --no-headers 2>/dev/null | awk '{printf "  %-25s %-15s %s\n", $1, $3, $2}' || true

echo ""
info "📊 Quick Commands:"
echo "  • View all pods:      kubectl get pods -n ${NAMESPACE}"
echo "  • View logs:          kubectl logs -n ${NAMESPACE} -l app=<service>"
echo "  • Check service:      kubectl get svc -n ${NAMESPACE}"
echo "  • Describe pod:        kubectl describe pod -n ${NAMESPACE} <pod-name>"

echo ""
success "Deployment complete! Services should be operational."
echo ""

