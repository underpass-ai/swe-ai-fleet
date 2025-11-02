# Makefile for e2e-tests job

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-tests
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

# Detect container builder (podman preferred over docker)
BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build
build:
	@echo "🏗️  Building $(IMAGE)..."
	cd ../../ && $(BUILDER) build \
		-f jobs/e2e-tests/Dockerfile \
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

.PHONY: run-local
run-local:
	@echo "🧪 Running e2e tests locally..."
	$(BUILDER) run --rm \
		--network host \
		-e CONTEXT_SERVICE_URL=localhost:50054 \
		-e ORCHESTRATOR_SERVICE_URL=localhost:50055 \
		-e NEO4J_URI=bolt://localhost:7687 \
		-e NEO4J_USERNAME=neo4j \
		-e NEO4J_PASSWORD=testpassword \
		-e VALKEY_HOST=localhost \
		-e VALKEY_PORT=6379 \
		$(IMAGE)

.PHONY: increment-version
increment-version:
	@echo "📈 Incrementing version..."
	@bash increment-version.sh

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build           - Build the container image"
	@echo "  push            - Push the image to registry"
	@echo "  build-push      - Build and push"
	@echo "  run-local       - Run tests locally with podman"
	@echo "  increment-version - Increment VERSION in Makefile"

