# ============================================================================
# SWE AI Fleet — Root Makefile
# ============================================================================
# Targets are organized in make/*.mk includes.
# Run `make help` to see all available commands.
# ============================================================================

# Script entrypoints
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

# Include target modules
include make/dev.mk
include make/test.mk
include make/service.mk
include make/e2e.mk
include make/deploy.mk

# ============================================================================
# Help Target (default)
# ============================================================================
.PHONY: help
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "SWE AI Fleet - Makefile Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(install-deps|generate-protos|clean-protos)"
	@echo ""
	@echo "Services:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "service-"
	@echo ""
	@echo "Testing:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(test$$|test-unit|test-unit-debug|test-module|test-all|e2e-)"
	@echo ""
	@echo "Deployment:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | grep -E "(deploy|list-services|persistence-clean|cluster-clear|service-image-prune|e2e-image-prune|runner-)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate-protos"
	@echo "  make generate-protos-module MODULE=services/orchestrator"
	@echo "  make test-unit"
	@echo "  make test-module MODULE=core/shared"
	@echo "  make service-build SERVICE=workspace"
	@echo "  make service-test-core SERVICE=workspace"
	@echo "  make deploy-build"
	@echo "  make deploy-build-no-cache"
	@echo "  make deploy"
	@echo "  make deploy-service SERVICE=planning"
	@echo "  make deploy-service SERVICE=vllm-server SKIP_BUILD=1 VLLM_SERVER_IMAGE=registry.example.com/ns/vllm-openai:cu13"
	@echo "  make runner-build PROFILE=all TAG=v0.1.0"
	@echo "  make cluster-clear"
	@echo "  make service-image-prune KEEP=2"
	@echo "  make e2e-image-prune KEEP=2"
	@echo ""
