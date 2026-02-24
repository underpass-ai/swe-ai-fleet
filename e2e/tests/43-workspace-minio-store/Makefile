# Makefile for E2E Test: Workspace MinIO Store

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-workspace-minio-store
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build push build-push deploy status logs delete help

build:
	@echo "Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/43-workspace-minio-store/Dockerfile \
		-t $(IMAGE) \
		-t $(LATEST) \
		.
	@echo "Built $(IMAGE)"

push:
	@echo "Pushing $(IMAGE)..."
	$(BUILDER) push $(IMAGE)
	$(BUILDER) push $(LATEST)
	@echo "Pushed $(IMAGE)"

build-push: build push

deploy:
	@echo "Deploying E2E test job..."
	kubectl delete job -n swe-ai-fleet e2e-workspace-minio-store --ignore-not-found
	kubectl apply -f job.yaml
	@echo "Job deployed"

status:
	kubectl get job -n swe-ai-fleet e2e-workspace-minio-store || echo "Job not found"
	@echo ""
	kubectl get pods -n swe-ai-fleet -l app=e2e-workspace-minio-store || echo "No pods found"

logs:
	kubectl logs -n swe-ai-fleet -l app=e2e-workspace-minio-store --tail=100 -f

delete:
	kubectl delete job -n swe-ai-fleet e2e-workspace-minio-store || true

help:
	@echo "Available targets:"
	@echo "  build      - Build the container image"
	@echo "  push       - Push the image to registry"
	@echo "  build-push - Build and push"
	@echo "  deploy     - Deploy test job"
	@echo "  status     - Check job status"
	@echo "  logs       - View test logs"
	@echo "  delete     - Delete test job"
