# make/tool.mk — Generic per-tool targets
# Delegates to each tool's own Makefile.
# Usage: make tool-build TOOL=fleetctl

.PHONY: tool-build tool-test tool-install tool-coverage-full tool-vet tool-docker-build tool-docker-push

_require-tool:
	@if [ -z "$(TOOL)" ]; then \
		echo "ERROR: TOOL parameter is required"; \
		echo "Usage: make tool-<target> TOOL=<name>"; \
		exit 1; \
	fi
	@if [ ! -f "tools/$(TOOL)/Makefile" ]; then \
		echo "ERROR: tools/$(TOOL)/Makefile not found"; \
		exit 1; \
	fi

tool-build: _require-tool ## Build a tool binary. Usage: make tool-build TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) build

tool-test: _require-tool ## Run a tool's unit tests. Usage: make tool-test TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) test

tool-install: _require-tool ## Install a tool to GOPATH/bin. Usage: make tool-install TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) install

tool-vet: _require-tool ## Run go vet on a tool. Usage: make tool-vet TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) vet

tool-coverage-full: _require-tool ## Generate full coverage for SonarCloud. Usage: make tool-coverage-full TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) coverage-full

tool-docker-build: _require-tool ## Build container image for a tool. Usage: make tool-docker-build TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) docker-build

tool-docker-push: _require-tool ## Push container image for a tool. Usage: make tool-docker-push TOOL=fleetctl
	@$(MAKE) -C tools/$(TOOL) docker-push
