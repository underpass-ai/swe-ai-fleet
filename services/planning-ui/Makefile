# Planning UI Makefile
# Builds and pushes the Astro-based Planning UI container image

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME := planning-ui
VERSION ?= v0.1.0
FQIN := $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
FQIN_LATEST := $(REGISTRY)/$(IMAGE_NAME):latest

# Detect container runtime (podman, buildah, or nerdctl)
BUILD_CMD := $(shell command -v podman 2>/dev/null || command -v buildah 2>/dev/null || command -v nerdctl 2>/dev/null || echo "echo 'No container runtime found'")
PUSH_CMD := $(shell command -v podman 2>/dev/null || command -v buildah 2>/dev/null || command -v nerdctl 2>/dev/null || echo "echo 'No container runtime found'")

.PHONY: build push all clean dev

all: build

build:
	@echo "Building $(FQIN)..."
	$(BUILD_CMD) build -t $(FQIN) -t $(FQIN_LATEST) .
	@echo "✓ Built $(FQIN)"

push: build
	@echo "Pushing $(FQIN)..."
	$(PUSH_CMD) push $(FQIN)
	$(PUSH_CMD) push $(FQIN_LATEST)
	@echo "✓ Pushed $(FQIN)"

dev:
	@echo "Starting development server..."
	npm run dev

clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist .astro node_modules
	@echo "✓ Cleaned"

help:
	@echo "Planning UI Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  build    - Build container image"
	@echo "  push     - Build and push container image"
	@echo "  dev      - Start development server"
	@echo "  clean    - Remove build artifacts"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY - Container registry (default: registry.underpassai.com/swe-ai-fleet)"
	@echo "  VERSION  - Image version tag (default: v0.1.0)"
	@echo ""
	@echo "Example:"
	@echo "  make build VERSION=v0.2.0"
	@echo "  make push"

