# Makefile for E2E Test: Workspace Toolchains Multi-language

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-workspace-toolchains-multilang
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build push build-push deploy status logs delete deploy-remote status-remote logs-remote delete-remote runtime-up runtime-down help

build:
	@echo "Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/17-workspace-toolchains-multilang/Dockerfile \
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
	kubectl apply -f job.yaml
	@echo "Job deployed"

deploy-remote: runtime-up
	@echo "Deploying remote E2E test job..."
	kubectl apply -f job.remote.yaml
	@echo "Remote job deployed"

status:
	kubectl get job -n swe-ai-fleet e2e-workspace-toolchains-multilang || echo "Job not found"
	@echo ""
	kubectl get pods -n swe-ai-fleet -l app=e2e-workspace-toolchains-multilang || echo "No pods found"

status-remote:
	kubectl get deployment -n swe-ai-fleet workspace-toolchains-e2e || echo "Runtime not found"
	@echo ""
	kubectl get job -n swe-ai-fleet e2e-workspace-toolchains-multilang-remote || echo "Remote job not found"
	@echo ""
	kubectl get pods -n swe-ai-fleet -l app=e2e-workspace-toolchains-multilang-remote || echo "No remote pods found"

logs:
	kubectl logs -n swe-ai-fleet -l app=e2e-workspace-toolchains-multilang --tail=100 -f

logs-remote:
	kubectl logs -n swe-ai-fleet -l app=e2e-workspace-toolchains-multilang-remote --tail=100 -f

delete:
	kubectl delete job -n swe-ai-fleet e2e-workspace-toolchains-multilang || true

delete-remote:
	kubectl delete job -n swe-ai-fleet e2e-workspace-toolchains-multilang-remote || true

runtime-up:
	kubectl apply -f workspace-toolchains-e2e.yaml

runtime-down:
	kubectl delete -f workspace-toolchains-e2e.yaml --ignore-not-found=true

help:
	@echo "Available targets:"
	@echo "  build      - Build the container image"
	@echo "  push       - Push the image to registry"
	@echo "  build-push - Build and push"
	@echo "  deploy     - Deploy the test job"
	@echo "  deploy-remote - Deploy remote mode job (uses workspace-toolchains-e2e runtime)"
	@echo "  status     - Check job status"
	@echo "  status-remote - Check remote runtime and job status"
	@echo "  logs       - View test logs"
	@echo "  logs-remote - View remote job logs"
	@echo "  delete     - Delete the test job"
	@echo "  delete-remote - Delete the remote job"
	@echo "  runtime-up - Deploy remote workspace runtime"
	@echo "  runtime-down - Remove remote workspace runtime"
