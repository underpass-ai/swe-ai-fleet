# Makefile for grpcui Interactive Testing Server

# Docker configuration
REGISTRY ?= registry.underpassai.com
IMAGE_NAME ?= swe-fleet/grpcui-server
VERSION ?= latest
DOCKER_ENGINE ?= podman

# gRPC target configuration
GRPC_TARGET ?= orchestrator.swe-ai-fleet.svc.cluster.local:50055

.PHONY: help build push deploy clean

help:
	@echo "grpcui Interactive Testing Server"
	@echo ""
	@echo "Available targets:"
	@echo "  build    - Build grpcui server container"
	@echo "  push     - Push container to registry"
	@echo "  deploy   - Deploy to Kubernetes cluster"
	@echo "  clean    - Remove local container images"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  VERSION=$(VERSION)"
	@echo "  DOCKER_ENGINE=$(DOCKER_ENGINE)"
	@echo "  GRPC_TARGET=$(GRPC_TARGET)"

build:
	@echo "Building grpcui server container..."
	@cd ../.. && $$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) build \
		-f scripts/specs/Dockerfile.grpcui-server \
		-t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		-t $(REGISTRY)/$(IMAGE_NAME):latest \
		.
	@echo "✓ Container built"

push:
	@echo "Pushing grpcui server to registry..."
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) push $(REGISTRY)/$(IMAGE_NAME):latest
	@echo "✓ Container pushed"

deploy:
	@echo "Deploying grpcui server to Kubernetes..."
	@kubectl apply -f ../../deploy/k8s/14a-grpcui-deployment.yaml
	@kubectl apply -f ../../deploy/k8s/14b-grpcui-service.yaml
	@kubectl apply -f ../../deploy/k8s/14c-grpcui-ingress.yaml
	@echo "✓ Deployment complete"
	@echo ""
	@echo "Waiting for certificate issuance..."
	@sleep 10
	@kubectl get certificate -n swe-ai-fleet grpcui-tls
	@echo ""
	@echo "Access grpcui at:"
	@echo "  https://grpcui.underpassai.com"

clean:
	@echo "Cleaning local container images..."
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || docker) rmi $(REGISTRY)/$(IMAGE_NAME):$(VERSION) $(REGISTRY)/$(IMAGE_NAME):latest 2>/dev/null || true
	@echo "✓ Cleaned"



