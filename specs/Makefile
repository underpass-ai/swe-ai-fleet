# Makefile for Proto Bundle Management

# Default registry
REGISTRY ?= registry.underpassai.com
IMAGE_NAME ?= swe-fleet/protos

# Version from VERSION file
VERSION := $(shell cat VERSION)
ifndef VERSION
    $(error VERSION file not found)
endif

# Scripts directory
SCRIPTS_DIR := scripts/specs

.PHONY: help lint breaking validate bump patch minor major docs generate clean dev-docker-build dev-docker-run dev-docker-shell

help:
	@echo "Proto Bundle Management"
	@echo ""
	@echo "Available targets:"
	@echo "  lint          - Lint proto files"
	@echo "  breaking      - Check for breaking changes"
	@echo "  validate      - Full validation (lint + breaking)"
	@echo "  bump          - Interactive version bump"
	@echo "  patch         - Bump patch version"
	@echo "  minor         - Bump minor version"
	@echo "  major         - Bump major version"
	@echo "  generate      - Generate code from protos"
	@echo "  dev-docker-build  - Build dev tools container"
	@echo "  dev-docker-run    - Run dev tools container"
	@echo "  dev-docker-shell  - Shell into dev tools container"
	@echo "  clean         - Clean generated files"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  VERSION=$(VERSION)"
	@echo "  DOCKER_ENGINE=podman (use podman or docker)"
	@echo ""
	@echo "Examples:"
	@echo "  make validate              # Validate before committing"
	@echo "  make minor                 # Bump minor version"
	@echo "  make dev-docker-build      # Build dev tools container"
	@echo "  make dev-docker-shell      # Shell into dev tools container"

# Lint proto files
lint:
	cd fleet && buf lint

# Check for breaking changes
breaking:
	cd fleet && buf breaking --against '.git#branch=main' || \
		echo "⚠️  Breaking changes detected or cannot check against main"

# Full validation
validate: lint breaking
	@echo ""
	@echo "✅ Validation complete"

# Interactive version bump
bump:
	@$(SCRIPTS_DIR)/version-bump.sh auto

# Version bumps
patch:
	@$(SCRIPTS_DIR)/version-bump.sh patch

minor:
	@$(SCRIPTS_DIR)/version-bump.sh minor

major:
	@$(SCRIPTS_DIR)/version-bump.sh major



# Generate code
generate: generate-protos

# Generate protobuf code
generate-protos:
	@buf generate buf.gen.yaml

# Clean generated files
clean:
	@rm -rf gen/
	@rm -f proto-bundle-*.bin
	@echo "✓ Cleaned generated files"

# Development Docker container
DEV_TOOLS_IMAGE ?= swfleet/dev-tools:latest
DOCKER_ENGINE ?= podman

dev-docker-build:
	@echo "Building dev tools container..."
	@cd .. && $$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) build \
		-f scripts/specs/Dockerfile.dev-tools \
		-t $(DEV_TOOLS_IMAGE) \
		-t registry.underpassai.com/swe-fleet/proto-tools:latest \
		-t registry.underpassai.com/swe-fleet/proto-tools:v1.0.0 \
		.
	@echo "✓ Dev tools container built: $(DEV_TOOLS_IMAGE)"
	@echo "✓ Also tagged as: registry.underpassai.com/swe-fleet/proto-tools:latest"
	@echo "✓ Also tagged as: registry.underpassai.com/swe-fleet/proto-tools:v1.0.0"

dev-docker-run:
	@echo "Running dev tools container..."
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) run -it --rm \
		-v $$(pwd)/../..:/workspace \
		-w /workspace/specs \
		$(DEV_TOOLS_IMAGE) \
		/bin/bash

dev-docker-shell:
	@echo "Launching interactive shell in dev tools container..."
	@echo "Workspace mounted at /workspace"
	@$$(command -v $(DOCKER_ENGINE) >/dev/null 2>&1 && echo $(DOCKER_ENGINE) || (echo "❌ Neither podman nor docker found" && exit 1)) run -it --rm \
		-v $$(pwd)/../..:/workspace \
		-w /workspace/specs \
		$(DEV_TOOLS_IMAGE) \
		/bin/bash

