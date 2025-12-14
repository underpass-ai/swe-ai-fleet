# Makefile for Planning UI Get Node Relations E2E Test

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-planning-ui-get-node-relations
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

# Detect container builder (podman preferred over docker)
BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build
build:
	@echo "🏗️  Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/01-planning-ui-get-node-relations/Dockerfile \
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
	@echo "🚀 Deploying E2E test job..."
	kubectl apply -f e2e/tests/01-planning-ui-get-node-relations/job.yaml
	@echo "✅ Job deployed"

.PHONY: status
status:
	@echo "📊 Checking job status..."
	kubectl get job -n swe-ai-fleet e2e-planning-ui-get-node-relations
	@echo ""
	@echo "📋 Pod status:"
	kubectl get pods -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations

.PHONY: logs
logs:
	@echo "📜 Showing test logs..."
	kubectl logs -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations --tail=100 -f

.PHONY: delete
delete:
	@echo "🗑️  Deleting job..."
	kubectl delete job -n swe-ai-fleet e2e-planning-ui-get-node-relations || true
	@echo "✅ Job deleted"

.PHONY: run-local
run-local:
	@echo "🧪 Running e2e test locally..."
	@if [ -z "$(TEST_NODE_ID)" ]; then \
		echo "❌ ERROR: TEST_NODE_ID environment variable is required"; \
		echo "   Example: make run-local TEST_NODE_ID=story-123"; \
		exit 1; \
	fi
	$(BUILDER) run --rm \
		--network host \
		-e CONTEXT_SERVICE_URL=localhost:50054 \
		-e TEST_NODE_ID=$(TEST_NODE_ID) \
		-e TEST_NODE_TYPE=$(TEST_NODE_TYPE) \
		-e TEST_DEPTH=$(TEST_DEPTH) \
		$(IMAGE)

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build           - Build the container image"
	@echo "  push            - Push the image to registry"
	@echo "  build-push      - Build and push"
	@echo "  deploy          - Deploy the test job to Kubernetes"
	@echo "  status          - Check job status"
	@echo "  logs            - View test logs"
	@echo "  delete          - Delete the test job"
	@echo "  run-local       - Run test locally (requires TEST_NODE_ID)"
	@echo ""
	@echo "Environment variables for run-local:"
	@echo "  TEST_NODE_ID    - Required: Node ID to test (project_id, epic_id, story_id, or task_id)"
	@echo "  TEST_NODE_TYPE  - Optional: Node type (default: Story)"
	@echo "  TEST_DEPTH      - Optional: Traversal depth (default: 2)"

