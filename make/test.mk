# make/test.mk — Testing targets

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
	@bash $(SCRIPTS_DIR)/test/test-module.sh $(MODULE)

test-all: test-unit ## Run all test suites (alias for test-unit)
