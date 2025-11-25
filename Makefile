# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps

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


fresh-redeploy:  ## Fresh redeploy of the application (use NO_CACHE=1 for --no-cache builds)
	@if [ "$(NO_CACHE)" = "1" ]; then \
		bash scripts/infra/fresh-redeploy.sh --no-cache; \
	else \
		bash scripts/infra/fresh-redeploy.sh; \
	fi

fast-redeploy:  ## Redeploy using cached layers (always cache-friendly)
	@NO_CACHE=0 bash scripts/infra/fresh-redeploy.sh