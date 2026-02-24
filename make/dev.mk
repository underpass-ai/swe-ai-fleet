# make/dev.mk — Development targets (install, protobuf generation)

.PHONY: install-deps generate-protos generate-protos-module clean-protos

install-deps: ## Install Python dependencies (all modules)
	@pip install --upgrade pip
	@bash $(SCRIPTS_DIR)/dev/install-modules.sh

generate-protos: ## Generate protobuf files for all modules
	@bash $(PROTOS_ALL_SCRIPT)

generate-protos-module: ## Generate protobuf files for a specific module. Usage: make generate-protos-module MODULE=services/orchestrator
	@if [ -z "$(MODULE)" ]; then \
		echo "ERROR: MODULE parameter is required"; \
		echo "Usage: make generate-protos-module MODULE=<module-path>"; \
		exit 1; \
	fi
	@bash $(SCRIPTS_DIR)/dev/generate-protos-module.sh $(MODULE)

clean-protos: ## Clean generated protobuf files
	@bash $(PROTOS_CLEAN_SCRIPT)
