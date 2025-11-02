# Planning Service Makefile

VERSION ?= v0.1.0
REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = planning
IMAGE_TAG = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)

# Detect build tool (podman, buildah, or docker)
BUILD_CMD := $(shell command -v podman 2>/dev/null || command -v buildah 2>/dev/null || command -v docker 2>/dev/null)

ifndef BUILD_CMD
$(error No container build tool found. Install podman, buildah, or docker)
endif

.PHONY: help
help:
	@echo "Planning Service - Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  generate-grpc  - Generate gRPC Python code from proto"
	@echo "  test-unit      - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run ruff linter"
	@echo "  build          - Build container image"
	@echo "  push           - Push image to registry"
	@echo "  clean          - Clean generated files"

.PHONY: generate-grpc
generate-grpc:
	@echo "📦 Generating gRPC code from ../../specs/fleet/planning/v2/planning.proto"
	@echo "Note: This is done automatically in Dockerfile and scripts/test/unit.sh"
	@echo "For manual generation during development:"
	@mkdir -p planning/gen
	@python -m grpc_tools.protoc \
		-I../../specs/fleet/planning/v2 \
		--python_out=planning/gen \
		--pyi_out=planning/gen \
		--grpc_python_out=planning/gen \
		../../specs/fleet/planning/v2/planning.proto
	@sed -i 's/^import planning_pb2/from . import planning_pb2/' planning/gen/planning_pb2_grpc.py
	@cat > planning/gen/__init__.py << 'EOF'
"""Generated gRPC code.

Do NOT commit to git - generated during build/test.
"""
EOF
	@echo "✅ gRPC code generated (planning/gen/)"

.PHONY: test-unit
test-unit:
	@echo "🧪 Running unit tests..."
	@python -m pytest tests/unit/ -v --cov=planning --cov-report=term-missing

.PHONY: test-integration
test-integration:
	@echo "🧪 Running integration tests..."
	@python -m pytest tests/integration/ -v -m integration

.PHONY: test
test: test-unit

.PHONY: lint
lint:
	@echo "🔍 Running ruff linter..."
	@ruff check . --fix

.PHONY: build
build:
	@echo "🐳 Building $(IMAGE_TAG)"
	@echo "Build context: project root (../../)"
	@cd ../.. && $(BUILD_CMD) build \
		--tag $(IMAGE_TAG) \
		--file services/planning/Dockerfile \
		.
	@echo "✅ Image built: $(IMAGE_TAG)"

.PHONY: push
push:
	@echo "📤 Pushing $(IMAGE_TAG)"
	@$(BUILD_CMD) push $(IMAGE_TAG)
	@echo "✅ Image pushed"

.PHONY: clean
clean:
	@echo "🧹 Cleaning generated files..."
	@rm -rf planning/gen/ __pycache__/ .pytest_cache/ htmlcov/ .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

