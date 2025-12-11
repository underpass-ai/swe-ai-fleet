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

.PHONY: help lint breaking validate bump patch minor major publish docs docs-html docs-serve docs-gen generate clean grpcui-serve dev-docker-build dev-docker-run dev-docker-shell

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
	@echo "  publish       - Build and publish proto bundle"
	@echo "  docs-html     - Generate markdown documentation"
	@echo "  docs-serve    - Serve documentation on localhost:8080"
	@echo "  generate      - Generate code from protos"
	@echo "  grpcui-serve  - Launch grpcui interactive API tester (requires grpcui)"
	@echo "  dev-docker-build  - Build dev tools container"
	@echo "  dev-docker-run    - Run dev tools container"
	@echo "  dev-docker-shell  - Shell into dev tools container"
	@echo "  clean         - Clean generated files"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  VERSION=$(VERSION)"
	@echo "  SERVICE=service-name  (for grpcui-serve)"
	@echo "  PORT=50055           (for grpcui-serve, default: 50055)"
	@echo "  DOCKER_ENGINE=podman (use podman or docker)"
	@echo ""
	@echo "Examples:"
	@echo "  make validate              # Validate before committing"
	@echo "  make minor publish         # Bump minor and publish"
	@echo "  make docs-html             # Generate markdown docs"
	@echo "  make docs-serve            # Serve docs locally"
	@echo "  make grpcui-serve          # Interactive API tester (all services)"
	@echo "  make grpcui-serve SERVICE=orchestrator"
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

# Publish proto bundle
publish:
	@$(SCRIPTS_DIR)/publish-proto-bundle.sh


# Generate HTML documentation
docs-html:
	@$(SCRIPTS_DIR)/generate-docs.sh

# Serve documentation locally
docs-serve:
	@echo "Serving proto docs at http://localhost:8080"
	@echo "Press Ctrl+C to stop"
	@$(SCRIPTS_DIR)/serve-docs.sh

# Generate documentation (alias)
docs-gen: docs-html

# Launch grpcui interactive API tester
grpcui-serve:
	@which grpcui >/dev/null 2>&1 || PATH="$$HOME/go/bin:$$HOME/.local/bin:$$(go env GOPATH 2>/dev/null)/bin:$$PATH" which grpcui >/dev/null 2>&1 || { \
		echo "❌ grpcui not found. Install it with:"; \
		echo "   bash scripts/install-grpcui.sh"; \
		echo ""; \
		echo "   Or with Go:"; \
		echo "   go install github.com/fullstorydev/grpcui/cmd/grpcui@latest"; \
		exit 1; \
	}
	@PATH="$$HOME/go/bin:$$HOME/.local/bin:$$(go env GOPATH 2>/dev/null)/bin:$$PATH" bash -c ' \
		SERVICE_SPEC=$$([ -n "$(SERVICE)" ] && echo "fleet/$(SERVICE)/v1/$(SERVICE).proto" || echo ""); \
		PORT="$${PORT:-50055}"; \
		HOST="$${HOST:-localhost}"; \
		echo "Launching grpcui interactive API tester..."; \
		echo "  Service: $${SERVICE:-all}"; \
		echo "  Target: $$HOST:$$PORT"; \
		echo ""; \
		if [ -n "$$SERVICE_SPEC" ] && [ -f "$$SERVICE_SPEC" ]; then \
			echo "Using proto file: $$SERVICE_SPEC"; \
			grpcui -plaintext -import-path fleet -proto $$SERVICE_SPEC $$HOST:$$PORT; \
		elif [ -f "$$SERVICE_SPEC" ]; then \
			echo "❌ Proto file not found: $$SERVICE_SPEC"; \
			exit 1; \
		else \
			echo "Using server reflection (requires reflection enabled on gRPC server)"; \
			echo "If reflection not enabled, specify SERVICE=name"; \
			grpcui -plaintext $$HOST:$$PORT; \
		fi \
	'

# Generate code
generate: generate-protos generate-asyncapi

# Generate protobuf code
generate-protos:
	@buf generate buf.gen.yaml

# Generate AsyncAPI models
generate-asyncapi:
	@bash scripts/specs/generate-asyncapi-models.sh

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

