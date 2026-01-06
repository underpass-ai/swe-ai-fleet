# Makefile for E2E Test: Restart & Redelivery Idempotency (B0.5)

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-restart-redelivery-idempotency
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

# Detect container builder (podman preferred over docker)
BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build
build:
	@echo "🏗️  Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/07-restart-redelivery-idempotency/Dockerfile \
		-t $(IMAGE) \
		-t $(LATEST) \
		.
	@echo "✅ Built $(IMAGE)"

.PHONY: push
push:
	@echo "📤 Pushing $(IMAGE)..."
	$(BUILDER) push $(IMAGE)
	$(BUILDER) push $(LATEST)
	@echo "✅ Pushed $(IMAGE)"

.PHONY: build-push
build-push: build push

.PHONY: deploy
deploy:
	@echo "🚀 Deploying e2e test job..."
	kubectl apply -f job.yaml
	@echo "✅ Job deployed"

.PHONY: status
status:
	@echo "📊 Checking job status..."
	kubectl get job -n swe-ai-fleet e2e-restart-redelivery-idempotency || echo "Job not found"
	@echo ""
	@echo "📋 Pod status:"
	kubectl get pods -n swe-ai-fleet -l app=e2e-restart-redelivery-idempotency || echo "No pods found"

.PHONY: logs
logs:
	@echo "📜 Showing job logs..."
	kubectl logs -n swe-ai-fleet -l app=e2e-restart-redelivery-idempotency --tail=100 -f

.PHONY: delete
delete:
	@echo "🗑️  Deleting job..."
	kubectl delete job -n swe-ai-fleet e2e-restart-redelivery-idempotency || true
	@echo "✅ Job deleted"

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build           - Build the container image"
	@echo "  push            - Push the image to registry"
	@echo "  build-push      - Build and push"
	@echo "  deploy          - Deploy the job to Kubernetes"
	@echo "  status          - Check job status"
	@echo "  logs            - View job logs"
	@echo "  delete          - Delete the job"
