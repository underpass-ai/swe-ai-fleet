# make/service.mk — Generic per-service targets
# Delegates to each service's own Makefile.
# Usage: make service-build SERVICE=workspace

.PHONY: service-build service-run service-test service-test-core \
        service-coverage service-coverage-full

_require-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make service-<target> SERVICE=<name>"; \
		exit 1; \
	fi
	@if [ ! -f "services/$(SERVICE)/Makefile" ]; then \
		echo "ERROR: services/$(SERVICE)/Makefile not found"; \
		exit 1; \
	fi

service-build: _require-service ## Build a service binary. Usage: make service-build SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) build

service-run: _require-service ## Run a service locally. Usage: make service-run SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) run

service-test: _require-service ## Run a service's unit tests. Usage: make service-test SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) test

service-test-core: _require-service ## Run core tests with coverage gate. Usage: make service-test-core SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) coverage-core COVERAGE_MIN=80

service-coverage: _require-service ## Generate service coverage report. Usage: make service-coverage SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) coverage

service-coverage-full: _require-service ## Generate full service coverage (SonarCloud). Usage: make service-coverage-full SERVICE=workspace
	@$(MAKE) -C services/$(SERVICE) coverage-full
