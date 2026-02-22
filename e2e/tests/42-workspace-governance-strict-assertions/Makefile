# Makefile for E2E Test: Workspace Governance Strict Assertions

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-workspace-governance-strict-assertions
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest
NAMESPACE ?= swe-ai-fleet
JOB_NAME = e2e-workspace-governance-strict-assertions

BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build push build-push deploy status logs delete help

build:
	@echo "Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/42-workspace-governance-strict-assertions/Dockerfile \
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

status:
	kubectl get job -n $(NAMESPACE) $(JOB_NAME) || echo "Job not found"
	@echo ""
	kubectl get pods -n $(NAMESPACE) -l app=$(JOB_NAME) || echo "No pods found"

logs:
	kubectl logs -n $(NAMESPACE) -l app=$(JOB_NAME) --tail=200 -f

delete:
	kubectl delete job -n $(NAMESPACE) $(JOB_NAME) --ignore-not-found=true

help:
	@echo "Available targets:"
	@echo "  build      - Build the container image"
	@echo "  push       - Push the image to registry"
	@echo "  build-push - Build and push"
	@echo "  deploy     - Deploy the test job"
	@echo "  status     - Check job and pod status"
	@echo "  logs       - Stream test logs"
	@echo "  delete     - Delete test job"
