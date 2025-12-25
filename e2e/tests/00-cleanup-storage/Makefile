# Makefile for E2E Cleanup Storage Job

PROJECT_ROOT := $(shell pwd)/../../..
BUILDER := /usr/bin/podman
REGISTRY := registry.underpassai.com/swe-ai-fleet
IMAGE_NAME := e2e-cleanup-storage
VERSION := v1.0.0
NAMESPACE := swe-ai-fleet

.PHONY: build push build-push deploy status logs delete help

help:
	@echo "E2E Cleanup Storage Job - Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  build       - Build Docker image"
	@echo "  push        - Push Docker image to registry"
	@echo "  build-push  - Build and push Docker image"
	@echo "  deploy      - Deploy job to Kubernetes"
	@echo "  status      - Check job status"
	@echo "  logs        - View job logs"
	@echo "  delete      - Delete job from Kubernetes"
	@echo "  clean       - Delete job and remove local image"

build:
	@echo "🏗️  Building $(IMAGE_NAME)..."
	cd $(PROJECT_ROOT) && $(BUILDER) build \
		-f e2e/tests/00-cleanup-storage/Dockerfile \
		-t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		-t $(REGISTRY)/$(IMAGE_NAME):latest \
		.
	@echo "✅ Built $(REGISTRY)/$(IMAGE_NAME):$(VERSION)"

push:
	@echo "📤 Pushing $(IMAGE_NAME)..."
	$(BUILDER) push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	$(BUILDER) push $(REGISTRY)/$(IMAGE_NAME):latest
	@echo "✅ Pushed $(REGISTRY)/$(IMAGE_NAME):$(VERSION)"

build-push: build push
	@echo "✅ Build and push complete"

deploy:
	@echo "🚀 Deploying cleanup storage job..."
	kubectl apply -f job.yaml
	@echo "✅ Job deployed"

status:
	@echo "📊 Job status:"
	@kubectl get job -n $(NAMESPACE) e2e-cleanup-storage || echo "Job not found"
	@echo ""
	@echo "📊 Pod status:"
	@kubectl get pods -n $(NAMESPACE) -l app=e2e-cleanup-storage || echo "No pods found"

logs:
	@echo "📋 Job logs:"
	@kubectl logs -n $(NAMESPACE) -l app=e2e-cleanup-storage --tail=100 || echo "No logs found"

delete:
	@echo "🗑️  Deleting cleanup storage job..."
	kubectl delete -f job.yaml --ignore-not-found=true
	@echo "✅ Job deleted"

clean: delete
	@echo "🧹 Cleaning up local image..."
	$(BUILDER) rmi $(REGISTRY)/$(IMAGE_NAME):$(VERSION) $(REGISTRY)/$(IMAGE_NAME):latest 2>/dev/null || true
	@echo "✅ Cleanup complete"


