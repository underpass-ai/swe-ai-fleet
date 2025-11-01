# Makefile for test-system-e2e Job

# Container registry
REGISTRY ?= registry.underpassai.com/swe-fleet

# Version/tag (defaults to latest)
VERSION ?= latest

# Job name
JOB_NAME ?= test-system-e2e

# Kubernetes namespace
NAMESPACE ?= swe-ai-fleet

# Check podman is available
ifeq ($(shell command -v podman 2> /dev/null),)
    $(error podman not found. Please install podman: sudo pacman -S podman)
endif

# Fail fast if registry is not configured
ifeq ($(REGISTRY),registry.yourdomain.com/swe-fleet)
    $(error Registry not configured! Please set REGISTRY=<your-registry>)
endif

# Image name
IMAGE := $(REGISTRY)/$(JOB_NAME):$(VERSION)

# Dockerfile location (relative to project root when cd ../../)
DOCKERFILE := jobs/test-system-e2e/Dockerfile

# Manifest location (relative to jobs/test-system-e2e directory)
MANIFEST := test-system-e2e.yaml

.PHONY: build push deploy observe logs status clean versions prune all help

help:
	@echo "Available targets:"
	@echo "  build    - Build the E2E test image"
	@echo "  push     - Push image to registry"
	@echo "  deploy   - Delete old job and apply new one"
	@echo "  observe  - Watch job logs (follow mode)"
	@echo "  logs     - Show latest job logs"
	@echo "  status   - Show job status"
	@echo "  clean    - Remove old job from cluster"
	@echo "  versions - List available image versions"
	@echo "  prune    - Clean up completed/failed jobs and pods"
	@echo "  all      - build + push + deploy"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  VERSION=$(VERSION)"
	@echo "  JOB_NAME=$(JOB_NAME)"
	@echo "  NAMESPACE=$(NAMESPACE)"
	@echo ""
	@echo "Examples:"
	@echo "  make all                    # Build, push, and deploy"
	@echo "  make deploy                 # Deploy only"
	@echo "  make observe                # Watch logs"
	@echo "  VERSION=v0.2.0 make all     # Use different version"

# Build the container image
# Note: Build context is project root (../../) so COPY specs/ and tests/ works
build:
	@echo "Building $(IMAGE) with podman..."
	@cd ../../ ; podman build -t $(IMAGE) \
		-f $(DOCKERFILE) \
		--build-arg SPECS_PATH=specs \
		--build-arg TEST_FILE=tests/e2e/test_system_e2e.py \
		--build-arg JOB_PATH=jobs/test-system-e2e \
		.
	@echo "✓ Image built: $(IMAGE)"

# Push to registry
push:
	@echo "Pushing $(IMAGE) to registry..."
	podman push $(IMAGE)
	@echo "✓ Image pushed: $(IMAGE)"

# Deploy job to cluster
# First deletes old job, then applies new manifest
deploy:
	@echo "Deploying $(JOB_NAME) to namespace $(NAMESPACE)..."
	@kubectl delete job $(JOB_NAME) -n $(NAMESPACE) --ignore-not-found=true || true
	@kubectl apply -f $(MANIFEST)
	@echo "✓ Job deployed"

# Watch job logs (follow mode)
observe:
	@echo "Watching logs for $(JOB_NAME)..."
	@kubectl logs -n $(NAMESPACE) -l app.kubernetes.io/name=$(JOB_NAME) --follow

# Show latest job logs (non-follow)
logs:
	@kubectl logs -n $(NAMESPACE) -l app.kubernetes.io/name=$(JOB_NAME) --tail=100

# Show job status
status:
	@echo "Job status:"
	@kubectl get job $(JOB_NAME) -n $(NAMESPACE) 2>/dev/null || echo "Job not found"
	@echo ""
	@echo "Pod status:"
	@kubectl get pods -n $(NAMESPACE) -l app.kubernetes.io/name=$(JOB_NAME)

# Clean up: remove job from cluster
clean:
	@echo "Cleaning up job $(JOB_NAME) in namespace $(NAMESPACE)..."
	@kubectl delete job $(JOB_NAME) -n $(NAMESPACE) --ignore-not-found=true
	@echo "✓ Cleanup complete"

# List available image versions
versions:
	@echo "Available versions for $(REGISTRY)/$(JOB_NAME):"
	@podman images --format "table {{.Tag}}\t{{.CreatedAt}}" $(REGISTRY)/$(JOB_NAME) 2>/dev/null | head -20 || echo "  No local images found"
	@echo ""
	@echo "To see remote versions:"
	@echo "  skopeo list-tags docker://$(REGISTRY)/$(JOB_NAME) 2>/dev/null || echo '  Install skopeo to query registry'"

# Clean up completed/failed jobs and pods
# Stop the specific job gracefully if running, then delete it
prune:
	@echo "Pruning job $(JOB_NAME) in namespace $(NAMESPACE)..."
	@echo "Stopping job gracefully if running..."
	@kubectl delete job $(JOB_NAME) -n $(NAMESPACE) --grace-period=30 --ignore-not-found=true
	@echo "✓ Prune complete"

# Full workflow: build + push + deploy
all: build push deploy
	@echo ""
	@echo "=========================================="
	@echo "✓ Build, push, and deploy complete!"
	@echo ""
	@echo "Monitor the job with:"
	@echo "  make observe"
	@echo "=========================================="

