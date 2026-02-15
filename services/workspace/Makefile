# Workspace Execution Service (Go)

SERVICE_NAME := workspace
BINARY_NAME := workspace-service
CMD_PATH := ./cmd/workspace
COVERAGE_FILE := coverage.out
COVERAGE_CORE_FILE := coverage-core.out
COVERAGE_MIN ?= 76

# Sandbox-safe defaults (override if needed)
export GOCACHE ?= /tmp/go-cache-workspace
export GOTMPDIR ?= /tmp/go-tmp-workspace

.PHONY: help run build test test-all test-core coverage coverage-core clean docker-build docker-push

help:
	@echo "Workspace service commands"
	@echo ""
	@echo "  make run                # Run service locally"
	@echo "  make build              # Build binary"
	@echo "  make test               # Run all unit tests"
	@echo "  make coverage           # Full-package coverage report (informational)"
	@echo "  make coverage-core      # Coverage gate for core execution packages"
	@echo "  make docker-build       # Build container image"
	@echo "  make docker-push        # Push container image"
	@echo ""
	@echo "Variables:"
	@echo "  COVERAGE_MIN=$(COVERAGE_MIN)"

run:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go run $(CMD_PATH)

build:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go build -o bin/$(BINARY_NAME) $(CMD_PATH)

test: test-all

test-all:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./...

test-core:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./internal/app ./internal/adapters/...

coverage:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./... -coverprofile=$(COVERAGE_FILE)
	go tool cover -func=$(COVERAGE_FILE)

coverage-core:
	@mkdir -p "$(GOCACHE)" "$(GOTMPDIR)"
	go test ./internal/app ./internal/adapters/... -coverprofile=$(COVERAGE_CORE_FILE)
	@go tool cover -func=$(COVERAGE_CORE_FILE) | tee /tmp/workspace-coverage-core.txt
	@COVERAGE_VALUE=$$(awk '/^total:/ {print $$3}' /tmp/workspace-coverage-core.txt | sed 's/%//'); \
	if awk "BEGIN {exit !($$COVERAGE_VALUE >= $(COVERAGE_MIN))}"; then \
		echo "Coverage gate passed: $$COVERAGE_VALUE% >= $(COVERAGE_MIN)%"; \
	else \
		echo "Coverage gate failed: $$COVERAGE_VALUE% < $(COVERAGE_MIN)%"; \
		exit 1; \
	fi

clean:
	rm -rf bin coverage*.out

docker-build:
	@BUILDER=$$(command -v podman 2>/dev/null || command -v docker 2>/dev/null); \
	if [ -z "$$BUILDER" ]; then \
		echo "No container builder found (podman or docker)"; \
		exit 1; \
	fi; \
	$$BUILDER build -f Dockerfile -t registry.underpassai.com/swe-ai-fleet/workspace:v0.1.0 -t registry.underpassai.com/swe-ai-fleet/workspace:latest ../..

docker-push:
	@BUILDER=$$(command -v podman 2>/dev/null || command -v docker 2>/dev/null); \
	if [ -z "$$BUILDER" ]; then \
		echo "No container builder found (podman or docker)"; \
		exit 1; \
	fi; \
	$$BUILDER push registry.underpassai.com/swe-ai-fleet/workspace:v0.1.0; \
	$$BUILDER push registry.underpassai.com/swe-ai-fleet/workspace:latest
