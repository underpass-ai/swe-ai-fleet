# Makefile for E2E Test: Validate Review Results Persistence

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-validate-review-results-persistence
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest
JOB_NAME = e2e-validate-review-results-persistence
NAMESPACE = swe-ai-fleet

# Detect container builder (podman preferred over docker)
BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: help build push deploy status logs delete clean

help:  ## Show this help message
	@echo "E2E Test: Validate Review Results Persistence"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build:  ## Build Docker image
	@echo "🔨 Building Docker image: $(IMAGE)..."
	cd ../../../../ && $(BUILDER) build \
		-f e2e/tests/auxiliary/07-validate-review-results-persistence/Dockerfile \
		-t $(IMAGE) \
		-t $(LATEST) \
		.
	@echo "✅ Built $(IMAGE)"

push:  ## Push Docker image
	@echo "📤 Pushing $(IMAGE)..."
	$(BUILDER) push $(IMAGE)
	$(BUILDER) push $(LATEST)
	@echo "✅ Pushed $(IMAGE)"

build-push: build push  ## Build and push Docker image

deploy: build-push  ## Build, push and deploy test job
	@echo "🚀 Deploying test job: $(JOB_NAME)"
	kubectl apply -f job.yaml
	@echo "✅ Job deployed: $(JOB_NAME)"
	@echo "📊 Check status with: make status"
	@echo "📋 View logs with: make logs"

status:  ## Show job status
	@echo "📊 Checking job status..."
	@kubectl get job -n $(NAMESPACE) $(JOB_NAME) || echo "Job not found"
	@echo ""
	@echo "📋 Pod status:"
	@kubectl get pods -n $(NAMESPACE) -l app=$(JOB_NAME) || echo "No pods found"

logs:  ## Show job logs (follow)
	@echo "📜 Showing job logs..."
	@kubectl logs -n $(NAMESPACE) -l app=$(JOB_NAME) --tail=100 -f

logs-last:  ## Show last job logs (no follow)
	@echo "📋 Last job logs:"
	@POD=$$(kubectl get pods -n $(NAMESPACE) -l app=$(JOB_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "❌ No pod found for job $(JOB_NAME)"; \
		exit 1; \
	fi; \
	kubectl logs -n $(NAMESPACE) $$POD --tail=500

delete:  ## Delete test job
	@echo "🗑️  Deleting job..."
	@kubectl delete job -n $(NAMESPACE) $(JOB_NAME) || true
	@echo "✅ Job deleted"

clean: delete  ## Delete job and remove local image
	@echo "🧹 Cleaning up local images..."
	@$(BUILDER) rmi $(IMAGE) 2>/dev/null || true
	@$(BUILDER) rmi $(LATEST) 2>/dev/null || true
	@echo "✅ Cleanup complete"
