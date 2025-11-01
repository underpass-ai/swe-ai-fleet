# Makefile for Proto Documentation Server

# Docker configuration
REGISTRY ?= registry.underpassai.com
IMAGE_NAME ?= swe-fleet/proto-docs-server
VERSION ?= latest
DOCKER_ENGINE ?= podman

.PHONY: help build push deploy clean

help:
	@echo "Proto Documentation Server"
	@echo ""
	@echo "Available targets:"
	@echo "  build    - Build docs server container"
	@echo "  push     - Push container to registry"
	@echo "  deploy   - Deploy to Kubernetes cluster"
	@echo "  clean    - Remove local container images"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  VERSION=$(VERSION)"
	@echo "  DOCKER_ENGINE=$(DOCKER_ENGINE)"

build:
	@echo "Building proto docs server container..."
	@cd ../.. && $$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) build \
		-f scripts/specs/Dockerfile.docs-server \
		-t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		-t $(REGISTRY)/$(IMAGE_NAME):latest \
		.
	@echo "✓ Container built"

push:
	@echo "Pushing proto docs server to registry..."
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) push $(REGISTRY)/$(IMAGE_NAME):latest
	@echo "✓ Container pushed"

deploy:
	@echo "Deploying proto docs server to Kubernetes..."
	@kubectl apply -f ../../deploy/k8s/13a-proto-docs-deployment.yaml
	@kubectl apply -f ../../deploy/k8s/13b-proto-docs-service.yaml
	@kubectl apply -f ../../deploy/k8s/13c-proto-docs-ingress.yaml
	@echo "✓ Deployment complete"
	@echo ""
	@echo "Access documentation at:"
	@echo "  https://proto-docs.underpassai.com"

clean:
	@echo "Cleaning local container images..."
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || docker) rmi $(REGISTRY)/$(IMAGE_NAME):$(VERSION) $(REGISTRY)/$(IMAGE_NAME):latest 2>/dev/null || true
	@echo "✓ Cleaned"

