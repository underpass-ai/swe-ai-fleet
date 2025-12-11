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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(install-deps|generate-protos|clean-protos)"
	@echo ""
	@echo "Testing:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(test|test-unit|test-integration|test-e2e|test-all)"
	@echo ""
	@echo "Deployment:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(deploy|list-services|fresh-redeploy|fast-redeploy)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate-protos                    # Generate protobuf files"
	@echo "  make test-unit                          # Run unit tests"
	@echo "  make deploy-service SERVICE=planning    # Deploy planning service (fresh)"
	@echo "  make deploy-service-fast SERVICE=planning  # Deploy planning service (fast)"
	@echo "  make list-services                      # List all available services"
	@echo ""

# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps generate-protos clean-protos

install-deps:  ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	@pip install --upgrade pip
	@pip install -e ".[grpc,dev]"
	@echo "📦 Installing service packages..."
	@for service_dir in services/*/; do \
		if [ -f "$$service_dir/pyproject.toml" ]; then \
			echo "  Installing $$(basename $$service_dir)..."; \
			pip install -e "$$service_dir" || true; \
		fi; \
	done
	@echo "✅ Dependencies installed"

generate-protos:  ## Generate protobuf files for all services (for tests/development)
	@echo "📦 Generating protobuf files..."
	@source scripts/test/_generate_protos.sh && generate_protobuf_files
	@echo "✅ Protobuf files generated in services/*/gen/"

clean-protos:  ## Clean generated protobuf files
	@echo "🧹 Cleaning protobuf files..."
	@source scripts/test/_generate_protos.sh && cleanup_protobuf_files
	@echo "✅ Protobuf files cleaned"

# ============================================================================
# Testing Targets
# ============================================================================
.PHONY: test test-unit test-unit-debug test-integration test-e2e test-all fast-redeploy

test: test-unit  ## Run unit tests (default)

test-unit:  ## Run unit tests with coverage and protobuf generation
	@bash scripts/test/unit.sh

test-integration:  ## Run integration tests with Podman
	@bash scripts/test/integration.sh

test-e2e:  ## Run end-to-end tests
	@bash scripts/test/e2e.sh


test-all:  ## Run all test suites (unit + integration + e2e)
	@bash scripts/test/all.sh


# ============================================================================
# Deployment Targets
# ============================================================================
.PHONY: fresh-redeploy fast-redeploy deploy-service deploy-service-fast deploy-service-skip-build list-services

fresh-redeploy:  ## Fresh redeploy of all services (no cache)
	@bash scripts/infra/fresh-redeploy-v2.sh --fresh

fast-redeploy:  ## Redeploy all services using cached layers (faster)
	@bash scripts/infra/fresh-redeploy-v2.sh --fast

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