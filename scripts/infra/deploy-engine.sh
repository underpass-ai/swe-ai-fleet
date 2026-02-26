#!/bin/bash
#
# Deploy Microservices Engine
#
# This script is the deployment engine used by scripts/infra/deploy.sh.
# It supports deploy-all or deploy-service, with optional cache mode,
# build-only mode, skip-build mode, and optional NATS reset.
#
# Usage:
#   ./deploy-engine.sh                          # Deploy all services (cache build)
#   ./deploy-engine.sh --service planning       # Deploy one service (cache build)
#   ./deploy-engine.sh --service planning --cache
#   ./deploy-engine.sh --service planning --no-cache
#   VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13 ./deploy-engine.sh --service vllm-server --skip-build
#   ./deploy-engine.sh --list-services
#   ./deploy-engine.sh --skip-build
#   ./deploy-engine.sh --reset-nats

set -euo pipefail

# Project root: use repo root (script lives in scripts/infra/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REGISTRY="registry.underpassai.com/swe-ai-fleet"
NAMESPACE="swe-ai-fleet"

# ============================================================================
# Service Configuration
# ============================================================================
# Keep in sync with deploy/k8s/30-microservices/*.yaml and 00-foundation/planning-ui.yaml.
# When adding a new service: add entries to all SERVICE_* arrays and ALL_SERVICES below.

# Base version tags (semantic versioning - will be incremented with timestamp on each build)
declare -A SERVICE_BASE_TAGS
SERVICE_BASE_TAGS["orchestrator"]="v3.0.0"
SERVICE_BASE_TAGS["ray-executor"]="v3.0.0"
SERVICE_BASE_TAGS["context"]="v2.0.0"
SERVICE_BASE_TAGS["planning"]="v2.0.0"
SERVICE_BASE_TAGS["planning-ui"]="v0.1.0"
SERVICE_BASE_TAGS["task-derivation"]="v0.1.0"
SERVICE_BASE_TAGS["backlog-review-processor"]="v0.1.0"
SERVICE_BASE_TAGS["planning-ceremony-processor"]="v0.1.0"
SERVICE_BASE_TAGS["workflow"]="v1.0.0"
SERVICE_BASE_TAGS["workspace"]="v0.1.0"
SERVICE_BASE_TAGS["fleet-proxy"]="v0.1.0"

# Map service names to their Dockerfile paths
declare -A SERVICE_DOCKERFILE
SERVICE_DOCKERFILE["orchestrator"]="services/orchestrator/Dockerfile"
SERVICE_DOCKERFILE["ray-executor"]="services/ray_executor/Dockerfile"
SERVICE_DOCKERFILE["context"]="services/context/Dockerfile"
SERVICE_DOCKERFILE["planning"]="services/planning/Dockerfile"
SERVICE_DOCKERFILE["planning-ui"]="services/planning-ui/Dockerfile"
SERVICE_DOCKERFILE["task-derivation"]="services/task_derivation/Dockerfile"
SERVICE_DOCKERFILE["backlog-review-processor"]="services/backlog_review_processor/Dockerfile"
SERVICE_DOCKERFILE["planning-ceremony-processor"]="services/planning_ceremony_processor/Dockerfile"
SERVICE_DOCKERFILE["workflow"]="services/workflow/Dockerfile"
SERVICE_DOCKERFILE["workspace"]="services/workspace/Dockerfile"
SERVICE_DOCKERFILE["fleet-proxy"]="services/fleet-proxy/Dockerfile"

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
SERVICE_YAML["planning-ceremony-processor"]="deploy/k8s/30-microservices/planning-ceremony-processor.yaml"
SERVICE_YAML["workspace"]="deploy/k8s/30-microservices/workspace.yaml"
SERVICE_YAML["vllm-server"]="deploy/k8s/30-microservices/vllm-server.yaml"
SERVICE_YAML["fleet-proxy"]="deploy/k8s/30-microservices/fleet-proxy.yaml"

# Map service names to container names in deployments (some differ from service name)
declare -A SERVICE_CONTAINER
SERVICE_CONTAINER["orchestrator"]="orchestrator"
SERVICE_CONTAINER["ray-executor"]="ray-executor"
SERVICE_CONTAINER["context"]="context"
SERVICE_CONTAINER["planning"]="planning"
SERVICE_CONTAINER["planning-ui"]="planning-ui"
SERVICE_CONTAINER["task-derivation"]="task-derivation"
SERVICE_CONTAINER["backlog-review-processor"]="backlog-review-processor"
SERVICE_CONTAINER["planning-ceremony-processor"]="planning-ceremony-processor"
SERVICE_CONTAINER["workflow"]="workflow"
SERVICE_CONTAINER["workspace"]="workspace"
SERVICE_CONTAINER["vllm-server"]="vllm"
SERVICE_CONTAINER["fleet-proxy"]="fleet-proxy"

# Map service names to registry image names (some use underscores)
declare -A SERVICE_IMAGE_NAME
SERVICE_IMAGE_NAME["orchestrator"]="orchestrator"
SERVICE_IMAGE_NAME["ray-executor"]="ray-executor"
SERVICE_IMAGE_NAME["context"]="context"
SERVICE_IMAGE_NAME["planning"]="planning"
SERVICE_IMAGE_NAME["planning-ui"]="planning-ui"
SERVICE_IMAGE_NAME["task-derivation"]="task-derivation"
SERVICE_IMAGE_NAME["backlog-review-processor"]="backlog-review-processor"
SERVICE_IMAGE_NAME["planning-ceremony-processor"]="planning-ceremony-processor"
SERVICE_IMAGE_NAME["workflow"]="workflow"
SERVICE_IMAGE_NAME["workspace"]="workspace"
SERVICE_IMAGE_NAME["fleet-proxy"]="fleet-proxy"

# Services that have NATS consumers (need graceful shutdown)
declare -A SERVICE_HAS_NATS
SERVICE_HAS_NATS["orchestrator"]=1
SERVICE_HAS_NATS["context"]=1
SERVICE_HAS_NATS["planning"]=1
SERVICE_HAS_NATS["workflow"]=1
SERVICE_HAS_NATS["task-derivation"]=1
SERVICE_HAS_NATS["backlog-review-processor"]=1
SERVICE_HAS_NATS["planning-ceremony-processor"]=1
SERVICE_HAS_NATS["ray-executor"]=0
SERVICE_HAS_NATS["planning-ui"]=0
SERVICE_HAS_NATS["workspace"]=0
SERVICE_HAS_NATS["vllm-server"]=0
SERVICE_HAS_NATS["fleet-proxy"]=0

# Services that don't need build (use external images)
declare -A SERVICE_NO_BUILD
SERVICE_NO_BUILD["vllm-server"]=1

# Pre-requisite YAMLs that must be applied BEFORE the main deployment YAML.
# These are typically cert-manager CRDs, PKI resources, or other dependencies.
declare -A SERVICE_PREREQ_YAML
SERVICE_PREREQ_YAML["fleet-proxy"]="deploy/k8s/30-microservices/fleet-proxy-pki.yaml"

# All available services
ALL_SERVICES=("orchestrator" "ray-executor" "context" "planning" "planning-ui" "workflow" "workspace" "task-derivation" "backlog-review-processor" "planning-ceremony-processor" "fleet-proxy" "vllm-server")

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
BUILD_ONLY=false
RESET_NATS=false
NO_CACHE=false  # Default to cached builds
LIST_SERVICES=false
VLLM_SERVER_IMAGE_OVERRIDE="${VLLM_SERVER_IMAGE:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --cache)
            NO_CACHE=false
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --service|-s)
            TARGET_SERVICE="$2"
            shift 2
            ;;
        --fast)
            # Backward-compatible alias of --cache.
            NO_CACHE=false
            shift
            ;;
        --fresh)
            # Backward-compatible alias of --no-cache.
            NO_CACHE=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
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
            echo "  --cache                Build using cache (default)"
            echo "  --no-cache             Build without cache"
            echo "  --fast                 Alias of --cache (legacy)"
            echo "  --fresh                Alias of --no-cache (legacy)"
            echo "  --skip-build           Skip building images (only redeploy existing images)"
            echo "  --build-only           Build and push images only (do not deploy)"
            echo "  --reset-nats           Also reset NATS streams (clean slate)"
            echo "  -l, --list-services    List all available services"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  VLLM_SERVER_IMAGE      Override image for vllm-server (e.g. registry.example.com/ns/vllm-openai:cu13)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Deploy all services (cache)"
            echo "  $0 --service planning                 # Deploy planning service (cache)"
            echo "  $0 --service planning --cache         # Deploy planning with cache"
            echo "  $0 --service planning --skip-build   # Redeploy planning without rebuilding"
            echo "  $0 --build-only --cache               # Build+push all services with cache"
            echo "  VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13 $0 --service vllm-server --skip-build"
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

if [ "$BUILD_ONLY" = true ] && [ "$SKIP_BUILD" = true ]; then
    fatal "Cannot use --build-only together with --skip-build"
fi

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

# Validate vLLM image override (if provided)
validate_vllm_image_override() {
    if [ -z "$VLLM_SERVER_IMAGE_OVERRIDE" ]; then
        return 0
    fi

    if [[ "$VLLM_SERVER_IMAGE_OVERRIDE" =~ [[:space:]] ]]; then
        fatal "VLLM_SERVER_IMAGE is invalid (contains spaces): ${VLLM_SERVER_IMAGE_OVERRIDE}"
    fi

    if [[ "$VLLM_SERVER_IMAGE_OVERRIDE" != *:* ]]; then
        warn "VLLM_SERVER_IMAGE has no explicit tag/digest: ${VLLM_SERVER_IMAGE_OVERRIDE}"
    fi
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
    echo "  $0 --service planning --cache"
    echo "  $0 --service orchestrator --no-cache"
    echo "  VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13 $0 --service vllm-server --skip-build"
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
    if [ "${SERVICE_NO_BUILD[$service]:-0}" = "1" ]; then
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

    local build_args=()
    if [ "$NO_CACHE" = true ]; then
        build_args=(--no-cache)
        info "Building ${service} (no-cache)..."
        if podman build "${build_args[@]}" -t "$image" -f "$dockerfile" . 2>&1 | tee -a "${BUILD_LOG}"; then
            success "${service} built successfully"
            return 0
        fi
        error "Failed to build ${service} (check ${BUILD_LOG})"
        return 1
    fi

    info "Building ${service} (cache)..."
    if podman build -t "$image" -f "$dockerfile" . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "${service} built successfully"
        return 0
    fi

    warn "${service} cache build failed, retrying with --no-cache..."
    if podman build --no-cache -t "$image" -f "$dockerfile" . 2>&1 | tee -a "${BUILD_LOG}"; then
        success "${service} built successfully (fallback no-cache)"
        return 0
    fi

    error "Failed to build ${service} after cache + no-cache fallback (check ${BUILD_LOG})"
    return 1
}

# Push image to registry (required for deploy: cluster pulls from REGISTRY)
push_service_image() {
    local service=$1
    local tag=$2

    # Skip push for services that don't need build
    if [ "${SERVICE_NO_BUILD[$service]:-0}" = "1" ]; then
        info "Skipping push for ${service} (uses external image)"
        return 0
    fi

    local image_name="${SERVICE_IMAGE_NAME[$service]}"
    local image="${REGISTRY}/${image_name}:${tag}"

    info "Pushing ${service} to ${REGISTRY}..."
    if podman push "$image"; then
        success "${service} pushed successfully"
        return 0
    else
        error "Failed to push ${service} to registry"
        return 1
    fi
}

# Update deployment
update_deployment() {
    local service=$1
    local tag=$2
    local yaml_file="${SERVICE_YAML[$service]}"

    # Services without build (e.g., vllm-server) only need YAML apply
    if [ "${SERVICE_NO_BUILD[$service]:-0}" = "1" ]; then
        info "Applying ${service} deployment (external image, no build needed)..."
        if ! kubectl apply -f "${PROJECT_ROOT}/${yaml_file}"; then
            error "Failed to apply ${service}"
            return 1
        fi

        # Optional image override for external-image services (currently vllm-server).
        if [ "$service" = "vllm-server" ] && [ -n "$VLLM_SERVER_IMAGE_OVERRIDE" ]; then
            local container="${SERVICE_CONTAINER[$service]}"
            info "Overriding ${service} image: ${VLLM_SERVER_IMAGE_OVERRIDE}"
            if ! kubectl set image deployment/"$service" \
                "${container}=${VLLM_SERVER_IMAGE_OVERRIDE}" \
                -n ${NAMESPACE}; then
                error "Failed to set image override for ${service}"
                return 1
            fi
        fi

        success "${service} applied successfully"
        return 0
    fi

    # Services with build need image update
    local container="${SERVICE_CONTAINER[$service]}"
    local image_name="${SERVICE_IMAGE_NAME[$service]}"
    local image="${REGISTRY}/${image_name}:${tag}"

    # Apply pre-requisite YAMLs (e.g. PKI/cert-manager resources) before the main deployment.
    local prereq="${SERVICE_PREREQ_YAML[$service]:-}"
    if [ -n "$prereq" ] && [ -f "${PROJECT_ROOT}/${prereq}" ]; then
        info "Applying prerequisite for ${service}: ${prereq}"
        if ! kubectl apply -f "${PROJECT_ROOT}/${prereq}"; then
            warn "Failed to apply prerequisite ${prereq} (continuing)"
        fi
        # Give cert-manager time to issue certificates.
        sleep 5
    fi

    # Always apply manifest first so env/configMap/secret changes are reconciled.
    if ! kubectl apply -f "${PROJECT_ROOT}/${yaml_file}"; then
        error "Failed to apply ${service} manifest ${yaml_file}"
        return 1
    fi

    if kubectl get deployment/"$service" -n ${NAMESPACE} >/dev/null 2>&1; then
        # Deployment exists - update image
        kubectl set image deployment/"$service" \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${service} updated" || warn "Failed to update ${service}"
    else
        # Deployment created by apply; set image as final step.
        info "${service} deployment not found after apply, creating image pin..."
        kubectl set image deployment/"$service" \
            ${container}=${image} \
            -n ${NAMESPACE} && success "${service} created and updated" || warn "Failed to create ${service}"
    fi
}

run_build_and_push_images() {
    step "STEP 4: Build images and push to registry (${REGISTRY})..."
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
}

# ============================================================================
# Main Execution
# ============================================================================

validate_vllm_image_override

# Handle list services request
if [ "$LIST_SERVICES" = true ]; then
    list_services
    exit 0
fi

# Get services to deploy
SERVICES_TO_DEPLOY=($(get_services_to_deploy))

if [ -n "$VLLM_SERVER_IMAGE_OVERRIDE" ]; then
    VLLM_SELECTED=false
    for service in "${SERVICES_TO_DEPLOY[@]}"; do
        if [ "$service" = "vllm-server" ]; then
            VLLM_SELECTED=true
            break
        fi
    done
    if [ "$VLLM_SELECTED" = false ]; then
        warn "VLLM_SERVER_IMAGE is set but vllm-server is not part of this deploy; override will be ignored."
    fi
else
    for service in "${SERVICES_TO_DEPLOY[@]}"; do
        if [ "$service" = "vllm-server" ]; then
            warn "Deploying vllm-server without VLLM_SERVER_IMAGE override; default image may fail on CUDA 13.1 hosts (Error 803)."
            break
        fi
    done
fi

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
    highlight "Build mode: no-cache"
else
    highlight "Build mode: cache"
fi

if [ "$SKIP_BUILD" = true ]; then
    highlight "Build: Skipped (using existing images)"
else
    highlight "Build: Enabled"
fi

if [ "$BUILD_ONLY" = true ]; then
    highlight "Execution: Build only (no deploy)"
fi

if [ -n "$VLLM_SERVER_IMAGE_OVERRIDE" ]; then
    highlight "vLLM image override: ${VLLM_SERVER_IMAGE_OVERRIDE}"
fi

echo ""

if [ "$BUILD_ONLY" = true ]; then
    run_build_and_push_images
    echo "════════════════════════════════════════════════════════"
    echo "  ✓ Build Complete (no deploy)"
    echo "════════════════════════════════════════════════════════"
    echo ""
    exit 0
fi

# ============================================================================
# STEP 0: Cleanup Zombie Pods
# ============================================================================

step "STEP 0: Cleaning up zombie pods..."

ZOMBIE_COUNT=0
if zombie_output="$(kubectl get pods -n "${NAMESPACE}" \
    --field-selector=status.phase=Unknown --no-headers 2>/dev/null)"; then
    if [ -n "$zombie_output" ]; then
        ZOMBIE_COUNT="$(echo "$zombie_output" | wc -l)"
        ZOMBIE_COUNT="${ZOMBIE_COUNT// /}"
    fi
fi

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
SCALE_DOWN_COUNT=0

for service in "${SERVICES_TO_DEPLOY[@]}"; do
    if [ "${SERVICE_HAS_NATS[$service]}" = "1" ]; then
        SERVICES_TO_SCALE_DOWN["$service"]=1
        REPLICAS=$(get_replica_count "$service")
        ORIGINAL_REPLICAS["$service"]=$REPLICAS
        info "Will scale down ${service} (currently ${REPLICAS} replicas)"
        SCALE_DOWN_COUNT=$((SCALE_DOWN_COUNT + 1))
    fi
done

# Scale down
if [ "$SCALE_DOWN_COUNT" -gt 0 ]; then
    for service in "${!SERVICES_TO_SCALE_DOWN[@]}"; do
        info "Scaling down ${service}..."
        kubectl scale deployment/"$service" -n ${NAMESPACE} --replicas=0 || true
    done
fi

if [ "$SCALE_DOWN_COUNT" -gt 0 ]; then
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
    run_build_and_push_images
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

if [ "$SCALE_DOWN_COUNT" -gt 0 ]; then
    for service in "${!SERVICES_TO_SCALE_DOWN[@]}"; do
        REPLICAS=${ORIGINAL_REPLICAS["$service"]:-1}
        info "Scaling up ${service} to ${REPLICAS} replicas..."
        kubectl scale deployment/"$service" -n ${NAMESPACE} --replicas=${REPLICAS} && \
            success "${service} scaled to ${REPLICAS}" || warn "Failed to scale ${service}"
    done
fi

if [ "$SCALE_DOWN_COUNT" -gt 0 ]; then
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
CRASH_LOOPS=0
if crash_output="$(kubectl get pods -n "${NAMESPACE}" \
    -l "$LABEL_SELECTOR" \
    --field-selector=status.phase!=Running 2>/dev/null)"; then
    CRASH_LOOPS="$(echo "$crash_output" | grep -c CrashLoopBackOff)" || CRASH_LOOPS=0
fi

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
    echo "  ✓ Deploy Complete!"
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
