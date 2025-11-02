REDIS_PASSWORD ?= swefleet-dev
WEB_IMG ?= localhost/swe-ai-fleet-web:local
NET ?= swe-net

# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps

install-deps:  ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	@pip install --upgrade pip
	@pip install -e ".[grpc,dev]"
	@echo "✅ Dependencies installed"

# ============================================================================
# Testing Targets
# ============================================================================
.PHONY: test test-unit test-integration test-e2e test-all

test: test-unit  ## Run unit tests (default)

test-unit:  ## Run unit tests with coverage and protobuf generation
	@bash scripts/test/unit.sh

test-integration:  ## Run integration tests with Podman
	@bash scripts/test/integration.sh

test-e2e:  ## Run end-to-end tests
	@bash scripts/test/e2e.sh


test-all:  ## Run all test suites (unit + integration + e2e)
	@bash scripts/test/all.sh
