# ============================================================================
# Script Entrypoints
# ============================================================================
SCRIPTS_DIR := scripts

PROTOS_ALL_SCRIPT := $(SCRIPTS_DIR)/protos/generate-all.sh
PROTOS_CLEAN_SCRIPT := $(SCRIPTS_DIR)/protos/clean-all.sh
E2E_IMAGES_SCRIPT := $(SCRIPTS_DIR)/e2e/images.sh
INFRA_DEPLOY_SCRIPT := $(SCRIPTS_DIR)/infra/deploy.sh
INFRA_PERSISTENCE_CLEAN_SCRIPT := $(SCRIPTS_DIR)/infra/persistence-clean.sh

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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(install-deps|generate-protos|generate-protos-module|clean-protos)"
	@echo ""
	@echo "Testing:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(test|test-unit|test-all|e2e-)"
	@echo ""
	@echo "Deployment:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(deploy|list-services|fresh-redeploy|fast-redeploy|with-e2e|persistence-clean)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate-protos"
	@echo "  make generate-protos-module MODULE=services/orchestrator"
	@echo "  make test-unit"
	@echo "  make test-module MODULE=core/shared"
	@echo "  make deploy-service SERVICE=planning"
	@echo "  make deploy-service-fast SERVICE=planning"
	@echo "  make deploy-service-skip-build SERVICE=vllm-server VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13"
	@echo "  make workspace-test-core"
	@echo "  make deploy-workspace"
	@echo "  make persistence-clean"
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
.PHONY: workspace-build workspace-run workspace-test workspace-test-core workspace-coverage deploy-workspace

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
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service workspace --fresh

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
.PHONY: fresh-redeploy fast-redeploy fresh-redeploy-with-e2e fast-redeploy-with-e2e deploy-service deploy-service-fast deploy-service-skip-build list-services persistence-clean

fresh-redeploy: ## Fresh redeploy: build (no cache), push to registry, apply k8s
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --fresh

fast-redeploy: ## Fast redeploy: build (cache), push to registry, apply k8s
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --fast

fresh-redeploy-with-e2e: ## Fresh redeploy of all services + rebuild E2E tests
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --fresh --with-e2e

fast-redeploy-with-e2e: ## Fast redeploy of all services + rebuild E2E tests
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --fast --with-e2e

deploy-service: ## Deploy one service: build (no cache), push/apply
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make deploy-service SERVICE=<service-name>"; \
		echo ""; \
		bash $(INFRA_DEPLOY_SCRIPT) list-services; \
		exit 1; \
	fi
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service $(SERVICE) --fresh

deploy-service-fast: ## Deploy one service: build (cache), push/apply
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make deploy-service-fast SERVICE=<service-name>"; \
		echo ""; \
		bash $(INFRA_DEPLOY_SCRIPT) list-services; \
		exit 1; \
	fi
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service $(SERVICE) --fast

deploy-service-skip-build: ## Redeploy without build
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make deploy-service-skip-build SERVICE=<service-name>"; \
		echo ""; \
		bash $(INFRA_DEPLOY_SCRIPT) list-services; \
		exit 1; \
	fi
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service $(SERVICE) --skip-build

persistence-clean: ## Full persistence cleanup: purge NATS streams + clean Neo4j and Valkey
	@bash $(INFRA_PERSISTENCE_CLEAN_SCRIPT)

list-services: ## List all available services for deployment
	@bash $(INFRA_DEPLOY_SCRIPT) list-services

# Default target
.DEFAULT_GOAL := help
