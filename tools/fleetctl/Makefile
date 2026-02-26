# fleetctl — Fleet Control CLI Tool

BINARY_NAME := fleetctl
CMD_PATH := ./cmd/fleetctl
COVERAGE_FILE := coverage.out
COVERAGE_FULL_FILE := coverage-full.out
VERSION ?= v0.1.0

# Sandbox-safe defaults (override if needed)
export GOCACHE ?= /tmp/go-cache-fleetctl
export GOTMPDIR ?= /tmp/go-tmp-fleetctl

.PHONY: help build test vet install clean coverage coverage-full docker-build docker-push

help: ## Show this help
	@echo "fleetctl commands"
	@echo ""
	@echo "  make build           # Build binary"
	@echo "  make test            # Run tests"
	@echo "  make vet             # Run go vet"
	@echo "  make install         # Install to GOPATH/bin"
	@echo "  make coverage        # Coverage report (informational)"
	@echo "  make coverage-full   # Full coverage for SonarCloud"
	@echo "  make docker-build    # Build container image"
	@echo "  make docker-push     # Push container image"
	@echo "  make clean           # Clean artifacts"

build: ## Build binary
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go build -ldflags "-X main.version=$(VERSION)" -o bin/$(BINARY_NAME) $(CMD_PATH)

test: ## Run tests
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./...

vet: ## Run go vet
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go vet ./...

install: ## Install to GOPATH/bin
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go install -ldflags "-X main.version=$(VERSION)" $(CMD_PATH)

coverage: ## Coverage report (informational)
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./... -coverprofile=$(COVERAGE_FILE)
	go tool cover -func=$(COVERAGE_FILE)

coverage-full: ## Full coverage for SonarCloud
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	-go test ./... -coverprofile=$(COVERAGE_FULL_FILE) -covermode=atomic
	@if [ -f "$(COVERAGE_FULL_FILE)" ]; then \
		go tool cover -func=$(COVERAGE_FULL_FILE) | tail -1; \
		echo "Full coverage report generated: $(COVERAGE_FULL_FILE)"; \
	else \
		echo "Warning: $(COVERAGE_FULL_FILE) was not generated"; \
	fi

clean: ## Clean artifacts
	rm -rf bin coverage*.out

docker-build: ## Build container image
	@BUILDER=$$(command -v podman 2>/dev/null || command -v docker 2>/dev/null); \
	if [ -z "$$BUILDER" ]; then \
		echo "No container builder found (podman or docker)"; \
		exit 1; \
	fi; \
	$$BUILDER build -f Dockerfile -t registry.underpassai.com/swe-ai-fleet/fleetctl:$(VERSION) -t registry.underpassai.com/swe-ai-fleet/fleetctl:latest ../..

docker-push: ## Push container image
	@BUILDER=$$(command -v podman 2>/dev/null || command -v docker 2>/dev/null); \
	if [ -z "$$BUILDER" ]; then \
		echo "No container builder found (podman or docker)"; \
		exit 1; \
	fi; \
	$$BUILDER push registry.underpassai.com/swe-ai-fleet/fleetctl:$(VERSION); \
	$$BUILDER push registry.underpassai.com/swe-ai-fleet/fleetctl:latest
