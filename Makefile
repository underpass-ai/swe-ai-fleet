# ============================================================================
# Help Target (default)
# ============================================================================
.PHONY: help

help:  ## Show this help message
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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(deploy|list-services|fresh-redeploy|fast-redeploy|with-e2e)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate-protos                    # Generate protobuf files for all modules"
	@echo "  make generate-protos-module MODULE=services/orchestrator  # Generate protos for one module"
	@echo "  make test-unit                          # Run unit tests"
	@echo "  make test-module MODULE=core/shared     # Test a specific module"
	@echo "  make deploy-service SERVICE=planning    # Deploy planning service (fresh)"
	@echo "  make deploy-service-fast SERVICE=planning  # Deploy planning service (fast)"
	@echo "  make list-services                      # List all available services"
	@echo ""

# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps generate-protos clean-protos

install-deps:  ## Install Python dependencies (all modules)
	@echo "📦 Installing Python dependencies..."
	@pip install --upgrade pip
	@bash scripts/install-modules.sh
	@echo "✅ All modules installed"

generate-protos:  ## Generate protobuf files for all services (for tests/development)
	@echo "📦 Generating protobuf files for all modules..."
	@for module in services/orchestrator services/context services/planning services/planning_ceremony_processor services/task_derivation services/ray_executor services/workflow services/backlog_review_processor; do \
		if [ -f "$$module/generate-protos.sh" ]; then \
			echo "  Generating protos for $$module..."; \
			bash "$$module/generate-protos.sh" || exit 1; \
		fi; \
	done
	@echo "✅ Protobuf files generated in services/*/gen/"

generate-protos-module:  ## Generate protobuf files for a specific module. Usage: make generate-protos-module MODULE=services/orchestrator
	@if [ -z "$(MODULE)" ]; then \
		echo "❌ Error: MODULE parameter is required"; \
		echo "Usage: make generate-protos-module MODULE=<module-path>"; \
		echo "Example: make generate-protos-module MODULE=services/orchestrator"; \
		exit 1; \
	fi
	@bash scripts/generate-protos-module.sh $(MODULE)

clean-protos:  ## Clean generated protobuf files
	@echo "🧹 Cleaning protobuf files..."
	@for module in services/orchestrator services/context services/planning services/planning_ceremony_processor services/task_derivation services/ray_executor services/workflow services/backlog_review_processor; do \
		if [ -d "$$module/gen" ]; then \
			echo "  Cleaning $$module/gen..."; \
			rm -rf "$$module/gen"; \
		fi; \
	done
	@echo "✅ Protobuf files cleaned"

# ============================================================================
# Testing Targets
# ============================================================================
.PHONY: test test-unit test-unit-debug test-module test-all fast-redeploy

test: test-unit  ## Run unit tests (default)

test-unit:  ## Run unit tests for all modules with coverage and protobuf generation
	@bash scripts/test/unit.sh

test-module:  ## Test a specific module. Usage: make test-module MODULE=core/shared
	@if [ -z "$(MODULE)" ]; then \
		echo "❌ Error: MODULE parameter is required"; \
		echo "Usage: make test-module MODULE=<module-path>"; \
		echo "Example: make test-module MODULE=core/shared"; \
		exit 1; \
	fi
	@bash scripts/test-module.sh $(MODULE)

test-all:  ## Run all test suites (unit tests only)
	@bash scripts/test/all.sh

# ============================================================================
# E2E Test Targets
# ============================================================================
.PHONY: e2e-build e2e-build-test e2e-push e2e-push-test e2e-build-push e2e-build-push-test

e2e-build:  ## Build all E2E test images
	@echo "🏗️  Building all E2E test images..."
	@for test_dir in e2e/tests/*/; do \
		if [ -f "$$test_dir/Makefile" ]; then \
			test_name=$$(basename $$test_dir); \
			echo "  Building $$test_name..."; \
			$(MAKE) -C "$$test_dir" build || exit 1; \
		fi; \
	done
	@echo "✅ All E2E test images built"

e2e-build-test:  ## Build a specific E2E test image. Usage: make e2e-build-test TEST=01-planning-ui-get-node-relations
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Error: TEST parameter is required"; \
		echo "Usage: make e2e-build-test TEST=<test-directory>"; \
		echo "Example: make e2e-build-test TEST=01-planning-ui-get-node-relations"; \
		exit 1; \
	fi
	@if [ ! -f "e2e/tests/$(TEST)/Makefile" ]; then \
		echo "❌ Error: Test directory e2e/tests/$(TEST) not found or has no Makefile"; \
		exit 1; \
	fi
	@echo "🏗️  Building E2E test: $(TEST)..."
	@$(MAKE) -C "e2e/tests/$(TEST)" build
	@echo "✅ E2E test $(TEST) built"

e2e-push:  ## Push all E2E test images
	@echo "📤 Pushing all E2E test images..."
	@for test_dir in e2e/tests/*/; do \
		if [ -f "$$test_dir/Makefile" ]; then \
			test_name=$$(basename $$test_dir); \
			echo "  Pushing $$test_name..."; \
			$(MAKE) -C "$$test_dir" push || exit 1; \
		fi; \
	done
	@echo "✅ All E2E test images pushed"

e2e-push-test:  ## Push a specific E2E test image. Usage: make e2e-push-test TEST=01-planning-ui-get-node-relations
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Error: TEST parameter is required"; \
		echo "Usage: make e2e-push-test TEST=<test-directory>"; \
		echo "Example: make e2e-push-test TEST=01-planning-ui-get-node-relations"; \
		exit 1; \
	fi
	@if [ ! -f "e2e/tests/$(TEST)/Makefile" ]; then \
		echo "❌ Error: Test directory e2e/tests/$(TEST) not found or has no Makefile"; \
		exit 1; \
	fi
	@echo "📤 Pushing E2E test: $(TEST)..."
	@$(MAKE) -C "e2e/tests/$(TEST)" push
	@echo "✅ E2E test $(TEST) pushed"

e2e-build-push:  ## Build and push all E2E test images
	@$(MAKE) e2e-build
	@$(MAKE) e2e-push

e2e-build-push-test:  ## Build and push a specific E2E test image. Usage: make e2e-build-push-test TEST=01-planning-ui-get-node-relations
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Error: TEST parameter is required"; \
		echo "Usage: make e2e-build-push-test TEST=<test-directory>"; \
		echo "Example: make e2e-build-push-test TEST=01-planning-ui-get-node-relations"; \
		exit 1; \
	fi
	@$(MAKE) e2e-build-test TEST=$(TEST)
	@$(MAKE) e2e-push-test TEST=$(TEST)

# ============================================================================
# Deployment Targets
# ============================================================================
.PHONY: fresh-redeploy fast-redeploy deploy-service deploy-service-fast deploy-service-skip-build list-services

fresh-redeploy:  ## Fresh redeploy of all services (no cache)
	@bash scripts/infra/fresh-redeploy-v2.sh --fresh

fast-redeploy:  ## Redeploy all services using cached layers (faster)
	@bash scripts/infra/fresh-redeploy-v2.sh --fast

fresh-redeploy-with-e2e:  ## Fresh redeploy of all services + rebuild E2E tests
	@bash scripts/infra/fresh-redeploy-v2.sh --fresh
	@echo ""
	@echo "🏗️  Rebuilding E2E test images..."
	@$(MAKE) e2e-build-push
	@echo "✅ Fresh redeploy completed (services + E2E tests)"

fast-redeploy-with-e2e:  ## Fast redeploy of all services + rebuild E2E tests
	@bash scripts/infra/fresh-redeploy-v2.sh --fast
	@echo ""
	@echo "🏗️  Rebuilding E2E test images..."
	@$(MAKE) e2e-build-push
	@echo "✅ Fast redeploy completed (services + E2E tests)"

# New v2 deployment commands (per-service)
deploy-service:  ## Deploy a specific microservice (fresh, no cache). Usage: make deploy-service SERVICE=planning
	@if [ -z "$(SERVICE)" ]; then \
		echo "❌ Error: SERVICE parameter is required"; \
		echo "Usage: make deploy-service SERVICE=<service-name>"; \
		echo ""; \
		echo "Available services:"; \
		bash scripts/infra/fresh-redeploy-v2.sh --list-services; \
		exit 1; \
	fi
	@bash scripts/infra/fresh-redeploy-v2.sh --service $(SERVICE) --fresh

deploy-service-fast:  ## Deploy a specific microservice (fast, with cache). Usage: make deploy-service-fast SERVICE=planning
	@if [ -z "$(SERVICE)" ]; then \
		echo "❌ Error: SERVICE parameter is required"; \
		echo "Usage: make deploy-service-fast SERVICE=<service-name>"; \
		echo ""; \
		echo "Available services:"; \
		bash scripts/infra/fresh-redeploy-v2.sh --list-services; \
		exit 1; \
	fi
	@bash scripts/infra/fresh-redeploy-v2.sh --service $(SERVICE) --fast

deploy-service-skip-build:  ## Redeploy a service without rebuilding (use existing images). Usage: make deploy-service-skip-build SERVICE=planning
	@if [ -z "$(SERVICE)" ]; then \
		echo "❌ Error: SERVICE parameter is required"; \
		echo "Usage: make deploy-service-skip-build SERVICE=<service-name>"; \
		echo ""; \
		echo "Available services:"; \
		bash scripts/infra/fresh-redeploy-v2.sh --list-services; \
		exit 1; \
	fi
	@bash scripts/infra/fresh-redeploy-v2.sh --service $(SERVICE) --skip-build

list-services:  ## List all available services for deployment
	@bash scripts/infra/fresh-redeploy-v2.sh --list-services

# Default target
.DEFAULT_GOAL := help