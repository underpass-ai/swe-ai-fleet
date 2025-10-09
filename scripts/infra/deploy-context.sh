#!/usr/bin/env bash
#
# Deploy Context Service to Kubernetes
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if namespace exists
if ! kubectl get namespace swe &> /dev/null; then
    log_error "Namespace 'swe' does not exist. Please create it first."
    exit 1
fi

log_info "Building Context Service Docker image..."
cd "$PROJECT_ROOT"
docker build -t localhost:5000/swe-ai-fleet/context:latest -f services/context/Dockerfile .

log_info "Pushing image to local registry..."
docker push localhost:5000/swe-ai-fleet/context:latest

log_info "Deploying Context Service to Kubernetes..."
kubectl apply -f deploy/k8s/context-service.yaml

log_info "Waiting for Context Service to be ready..."
kubectl rollout status deployment/context -n swe --timeout=5m

log_info "✓ Context Service deployed successfully!"

# Show service status
log_info "Service status:"
kubectl get pods -n swe -l app=context
kubectl get svc -n swe -l app=context

log_info ""
log_info "To test the service:"
log_info "  kubectl port-forward -n swe svc/context 50054:50054"
log_info "  grpcurl -plaintext -d '{\"story_id\":\"test\",\"role\":\"DEV\",\"phase\":\"BUILD\"}' localhost:50054 fleet.context.v1.ContextService/GetContext"

log_info ""
log_info "To view logs:"
log_info "  kubectl logs -n swe -l app=context -f"

