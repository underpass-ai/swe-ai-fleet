# ============================================================================
# Script Entrypoints
# ============================================================================
SCRIPTS_DIR := scripts

PROTOS_ALL_SCRIPT := $(SCRIPTS_DIR)/protos/generate-all.sh
PROTOS_CLEAN_SCRIPT := $(SCRIPTS_DIR)/protos/clean-all.sh
E2E_IMAGES_SCRIPT := $(SCRIPTS_DIR)/e2e/images.sh
E2E_IMAGE_PRUNE_SCRIPT := $(SCRIPTS_DIR)/e2e/prune-images.sh
WORKSPACE_RUNNER_IMAGES_SCRIPT := $(SCRIPTS_DIR)/workspace/runner-images.sh
INFRA_DEPLOY_SCRIPT := $(SCRIPTS_DIR)/infra/deploy.sh
INFRA_PERSISTENCE_CLEAN_SCRIPT := $(SCRIPTS_DIR)/infra/persistence-clean.sh
INFRA_CLUSTER_CLEAR_SCRIPT := $(SCRIPTS_DIR)/infra/cluster-clear.sh
INFRA_SERVICE_IMAGE_PRUNE_SCRIPT := $(SCRIPTS_DIR)/infra/prune-service-images.sh

# ============================================================================
# Help Target (default)
# ============================================================================
.PHONY: help

help: ## Show this help message
	@echo "SWE AI Fleet - Makefile Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(install-deps|generate-protos|generate-protos-module|clean-protos)"
	@echo ""
	@echo "Testing:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(workspace-test|workspace-test-core|test$$|test-unit|test-unit-debug|test-module|test-all|e2e-)"
	@echo ""
	@echo "Deployment:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(deploy|deploy-build|workspace-runner|list-services|persistence-clean|cluster-clear|service-image-prune|e2e-image-prune)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate-protos"
	@echo "  make generate-protos-module MODULE=services/orchestrator"
	@echo "  make test-unit"
	@echo "  make test-module MODULE=core/shared"
	@echo "  make deploy-build"
	@echo "  make deploy-build-no-cache"
	@echo "  make deploy"
	@echo "  make deploy-service SERVICE=planning"
	@echo "  make deploy-service SERVICE=vllm-server SKIP_BUILD=1 VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13"
	@echo "  make workspace-test-core"
	@echo "  make workspace-runner-build PROFILE=all TAG=v0.1.0"
	@echo "  make cluster-clear"
	@echo "  make service-image-prune KEEP=2"
	@echo "  make e2e-image-prune KEEP=2"
	@echo ""

# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps generate-protos generate-protos-module clean-protos

install-deps: ## Install Python dependencies (all modules)
	@pip install --upgrade pip
	@bash $(SCRIPTS_DIR)/install-modules.sh

generate-protos: ## Generate protobuf files for all modules
	@bash $(PROTOS_ALL_SCRIPT)

generate-protos-module: ## Generate protobuf files for a specific module. Usage: make generate-protos-module MODULE=services/orchestrator
	@if [ -z "$(MODULE)" ]; then \
		echo "ERROR: MODULE parameter is required"; \
		echo "Usage: make generate-protos-module MODULE=<module-path>"; \
		exit 1; \
	fi
	@bash $(SCRIPTS_DIR)/generate-protos-module.sh $(MODULE)

clean-protos: ## Clean generated protobuf files
	@bash $(PROTOS_CLEAN_SCRIPT)

# ============================================================================
# Workspace Service (Go) Targets
# ============================================================================
.PHONY: workspace-build workspace-run workspace-test workspace-test-core workspace-coverage deploy-workspace workspace-runner-list workspace-runner-build workspace-runner-push workspace-runner-build-push

workspace-build: ## Build workspace service binary
	@$(MAKE) -C services/workspace build

workspace-run: ## Run workspace service locally
	@$(MAKE) -C services/workspace run

workspace-test: ## Run workspace service unit tests
	@$(MAKE) -C services/workspace test

workspace-test-core: ## Run workspace core unit tests with 80% coverage gate
	@$(MAKE) -C services/workspace coverage-core COVERAGE_MIN=80

workspace-coverage: ## Generate workspace coverage reports
	@$(MAKE) -C services/workspace coverage

deploy-workspace: ## Deploy workspace service via standard deploy pipeline
	@$(MAKE) deploy-service SERVICE=workspace NO_CACHE=$${NO_CACHE:-0} SKIP_BUILD=$${SKIP_BUILD:-0} RESET_NATS=$${RESET_NATS:-0}

workspace-runner-list: ## List workspace runner image profiles and tags
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) list --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0}

workspace-runner-build: ## Build workspace runner images. Usage: make workspace-runner-build PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) build --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${NO_CACHE:+--no-cache} $${TAG_LATEST:+--tag-latest}

workspace-runner-push: ## Push workspace runner images. Usage: make workspace-runner-push PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) push --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${TAG_LATEST:+--tag-latest}

workspace-runner-build-push: ## Build and push workspace runner images. Usage: make workspace-runner-build-push PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) build-push --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${NO_CACHE:+--no-cache} $${TAG_LATEST:+--tag-latest}

# ============================================================================
# Testing Targets
# ============================================================================
.PHONY: test test-unit test-unit-debug test-module test-all

test: test-unit ## Run unit tests (default)

test-unit: ## Run unit tests for all modules with coverage and protobuf generation
	@bash $(SCRIPTS_DIR)/test/unit.sh

test-unit-debug: ## Run unit tests in debug mode (verbose, no capture, long tracebacks)
	@bash $(SCRIPTS_DIR)/test/unit-debug.sh

test-module: ## Test a specific module. Usage: make test-module MODULE=core/shared
	@if [ -z "$(MODULE)" ]; then \
		echo "ERROR: MODULE parameter is required"; \
		echo "Usage: make test-module MODULE=<module-path>"; \
		exit 1; \
	fi
	@bash $(SCRIPTS_DIR)/test-module.sh $(MODULE)

test-all: ## Run all test suites (unit tests only)
	@bash $(SCRIPTS_DIR)/test/all.sh

# ============================================================================
# E2E Test Targets
# ============================================================================
.PHONY: e2e-run e2e-build e2e-build-test e2e-push e2e-push-test e2e-build-push e2e-build-push-test e2e-ephemeral-up e2e-ephemeral-down e2e-ephemeral-status

e2e-run: ## Run E2E tests sequentially (Kubernetes jobs)
	@bash e2e/run-e2e-tests.sh

e2e-build: ## Build all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) build

e2e-build-test: ## Build a specific E2E test image. Usage: make e2e-build-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-build-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) build --test $(TEST)

e2e-push: ## Push all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) push

e2e-push-test: ## Push a specific E2E test image. Usage: make e2e-push-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-push-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) push --test $(TEST)

e2e-build-push: ## Build and push all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) build-push

e2e-build-push-test: ## Build and push a specific E2E test image. Usage: make e2e-build-push-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-build-push-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) build-push --test $(TEST)

e2e-ephemeral-up: ## Deploy ephemeral E2E deps (mongo/postgres/kafka/rabbit/nats)
	@bash e2e/auxiliary/ephemeral-deps.sh up

e2e-ephemeral-down: ## Delete ephemeral E2E deps (mongo/postgres/kafka/rabbit/nats)
	@bash e2e/auxiliary/ephemeral-deps.sh down

e2e-ephemeral-status: ## Show ephemeral E2E deps status
	@bash e2e/auxiliary/ephemeral-deps.sh status

# ============================================================================
# Deployment Targets
# ============================================================================
.PHONY: deploy-build deploy-build-no-cache deploy deploy-service list-services persistence-clean cluster-clear service-image-prune e2e-image-prune

deploy-build: ## Build+push all services using cache (no deploy)
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --cache --build-only

deploy-build-no-cache: ## Build+push all services without cache (no deploy)
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --no-cache --build-only

deploy: ## Single deploy command for all services. Optional: NO_CACHE=1 SKIP_BUILD=1 RESET_NATS=1 WITH_E2E=1
	@opts="--cache"; \
	if [ "$${NO_CACHE:-0}" = "1" ]; then opts="--no-cache"; fi; \
	if [ "$${SKIP_BUILD:-0}" = "1" ]; then opts="$$opts --skip-build"; fi; \
	if [ "$${RESET_NATS:-0}" = "1" ]; then opts="$$opts --reset-nats"; fi; \
	if [ "$${WITH_E2E:-0}" = "1" ]; then opts="$$opts --with-e2e"; fi; \
	VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all $$opts

deploy-service: ## Deploy one service. Usage: make deploy-service SERVICE=<name> [NO_CACHE=1] [SKIP_BUILD=1] [RESET_NATS=1]
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make deploy-service SERVICE=<service-name>"; \
		echo ""; \
		bash $(INFRA_DEPLOY_SCRIPT) list-services; \
		exit 1; \
	fi
	@opts="--cache"; \
	if [ "$${NO_CACHE:-0}" = "1" ]; then opts="--no-cache"; fi; \
	if [ "$${SKIP_BUILD:-0}" = "1" ]; then opts="$$opts --skip-build"; fi; \
	if [ "$${RESET_NATS:-0}" = "1" ]; then opts="$$opts --reset-nats"; fi; \
	VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service $(SERVICE) $$opts

persistence-clean: ## Full persistence cleanup: purge NATS streams + clean Neo4j and Valkey
	@bash $(INFRA_PERSISTENCE_CLEAN_SCRIPT)

cluster-clear: ## Clear jobs + Valkey/NATS/Neo4j + MinIO workspace buckets
	@bash $(INFRA_CLUSTER_CLEAR_SCRIPT)

service-image-prune: ## Delete old service image tags, keeping latest N tags per image (default KEEP=2)
	@KEEP="$${KEEP:-2}" DRY_RUN="$${DRY_RUN:-0}" REGISTRY="$${REGISTRY:-registry.underpassai.com/swe-ai-fleet}" bash $(INFRA_SERVICE_IMAGE_PRUNE_SCRIPT)

e2e-image-prune: ## Delete old E2E job image tags, keeping latest N tags per image (default KEEP=2)
	@KEEP="$${KEEP:-2}" DRY_RUN="$${DRY_RUN:-0}" REGISTRY="$${REGISTRY:-registry.underpassai.com/swe-ai-fleet}" bash $(E2E_IMAGE_PRUNE_SCRIPT)

list-services: ## List all available services for deployment
	@bash $(INFRA_DEPLOY_SCRIPT) list-services

# Default target
.DEFAULT_GOAL := help
