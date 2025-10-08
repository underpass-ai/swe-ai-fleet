# Makefile for SWE AI Fleet Microservices

PROTO_DIR := ../specs
GO_OUT := .
PY_OUT := ../workers/pyclients

# Container registry
REGISTRY ?= registry.underpassai.com/swe-fleet

# Version/tag
VERSION ?= v0.1.0

# Container engine detection (podman, buildah, nerdctl)
# Priority: podman > buildah > nerdctl
CONTAINER_ENGINE ?= auto

ifeq ($(CONTAINER_ENGINE),auto)
    ifneq ($(shell command -v podman 2> /dev/null),)
        CONTAINER_ENGINE := podman
        BUILD_CMD := podman build
        PUSH_CMD := podman push
    else ifneq ($(shell command -v buildah 2> /dev/null),)
        CONTAINER_ENGINE := buildah
        BUILD_CMD := buildah bud
        PUSH_CMD := buildah push
    else ifneq ($(shell command -v nerdctl 2> /dev/null),)
        CONTAINER_ENGINE := nerdctl
        BUILD_CMD := nerdctl build
        PUSH_CMD := nerdctl push
    else
        $(error No container build tool found. Install podman, buildah, or nerdctl)
    endif
else ifeq ($(CONTAINER_ENGINE),podman)
    BUILD_CMD := podman build
    PUSH_CMD := podman push
else ifeq ($(CONTAINER_ENGINE),buildah)
    BUILD_CMD := buildah bud
    PUSH_CMD := buildah push
else ifeq ($(CONTAINER_ENGINE),nerdctl)
    BUILD_CMD := nerdctl build
    PUSH_CMD := nerdctl push
else ifeq ($(CONTAINER_ENGINE),crio)
    # CRI-O doesn't have a build command, use buildah
    BUILD_CMD := buildah bud
    PUSH_CMD := buildah push
else ifeq ($(CONTAINER_ENGINE),containerd)
    # containerd uses nerdctl for Docker-compatible CLI
    BUILD_CMD := nerdctl build
    PUSH_CMD := nerdctl push
else
    $(error Unknown CONTAINER_ENGINE: $(CONTAINER_ENGINE). Use: podman, buildah, nerdctl, crio, or containerd)
endif

# Proto files
PROTOS := $(PROTO_DIR)/planning.proto \
          $(PROTO_DIR)/context.proto \
          $(PROTO_DIR)/storycoach.proto \
          $(PROTO_DIR)/workspace.proto

.PHONY: all gen gen-go gen-py clean lint test docker-build docker-push k8s-deploy

all: gen lint

# Generate all client/server code
gen: gen-go gen-py
	@echo "✓ Code generation complete"

# Generate Go gRPC code
gen-go:
	@echo "Generating Go gRPC code..."
	@mkdir -p planning/gen context/gen storycoach/gen workspace/gen
	@for proto in $(PROTOS); do \
		protoc -I $(PROTO_DIR) \
			--go_out=$(GO_OUT) \
			--go_opt=paths=source_relative \
			--go-grpc_out=$(GO_OUT) \
			--go-grpc_opt=paths=source_relative \
			$$proto; \
	done
	@echo "✓ Go code generated"

# Generate Python gRPC code
gen-py:
	@echo "Generating Python gRPC code..."
	@mkdir -p $(PY_OUT)
	@for proto in $(PROTOS); do \
		python -m grpc_tools.protoc -I $(PROTO_DIR) \
			--python_out=$(PY_OUT) \
			--pyi_out=$(PY_OUT) \
			--grpc_python_out=$(PY_OUT) \
			$$proto; \
	done
	@echo "✓ Python code generated"

# Lint Go code
lint:
	@echo "Linting Go services..."
	@cd planning && go vet ./... || true
	@cd storycoach && go vet ./... || true
	@cd workspace && go vet ./... || true
	@echo "✓ Linting complete"

# Format Go code
fmt:
	@echo "Formatting Go code..."
	@cd planning && go fmt ./...
	@cd storycoach && go fmt ./...
	@cd workspace && go fmt ./...
	@echo "✓ Formatting complete"

# Install Go dependencies
deps:
	@echo "Installing Go dependencies..."
	@cd planning && go mod tidy && go mod download || true
	@cd storycoach && go mod tidy && go mod download || true
	@cd workspace && go mod tidy && go mod download || true
	@cd pkg/natsx && go mod tidy && go mod download || true
	@echo "✓ Dependencies installed"

# Build all services
build:
	@echo "Building services..."
	@mkdir -p bin
	@cd planning/cmd && go build -o ../../bin/planning .
	@cd storycoach/cmd && go build -o ../../bin/storycoach .
	@cd workspace/cmd && go build -o ../../bin/workspace .
	@echo "✓ Build complete"

# Run tests
test:
	@echo "Running tests..."
	@cd planning && go test -v ./... || true
	@cd storycoach && go test -v ./... || true
	@cd workspace && go test -v ./... || true
	@echo "✓ Tests complete"

# Docker builds
docker-build: docker-build-planning docker-build-storycoach docker-build-workspace docker-build-worker docker-build-agent-workspace

docker-build-planning:
	@echo "Building Planning service image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/planning:$(VERSION) \
		-f planning/Dockerfile \
		--build-arg VERSION=$(VERSION) \
		..
	@echo "✓ Planning image built"

docker-build-storycoach:
	@echo "Building Story Coach service image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/storycoach:$(VERSION) \
		-f storycoach/Dockerfile \
		--build-arg VERSION=$(VERSION) \
		..
	@echo "✓ Story Coach image built"

docker-build-workspace:
	@echo "Building Workspace Scorer service image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/workspace:$(VERSION) \
		-f workspace/Dockerfile \
		--build-arg VERSION=$(VERSION) \
		..
	@echo "✓ Workspace image built"

docker-build-worker:
	@echo "Building Workspace Runner image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/workspace-runner:$(VERSION) \
		-f ../workers/Dockerfile \
		../workers
	@echo "✓ Workspace Runner image built"

docker-build-agent-workspace:
	@echo "Building Agent Workspace image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/agent-workspace:tooling-2025.10 \
		-f ../deploy/docker/agent-workspace/Dockerfile \
		../deploy/docker/agent-workspace
	@echo "✓ Agent Workspace image built"

docker-build-ui:
	@echo "Building UI image with $(CONTAINER_ENGINE)..."
	$(BUILD_CMD) -t $(REGISTRY)/po-ui:$(VERSION) \
		-f ../ui/po-react/Dockerfile \
		../ui/po-react
	@echo "✓ UI image built"

# Push all images
docker-push:
	@echo "Pushing images with $(CONTAINER_ENGINE)..."
	$(PUSH_CMD) $(REGISTRY)/planning:$(VERSION)
	$(PUSH_CMD) $(REGISTRY)/storycoach:$(VERSION)
	$(PUSH_CMD) $(REGISTRY)/workspace:$(VERSION)
	$(PUSH_CMD) $(REGISTRY)/workspace-runner:$(VERSION)
	$(PUSH_CMD) $(REGISTRY)/agent-workspace:tooling-2025.10
	$(PUSH_CMD) $(REGISTRY)/po-ui:$(VERSION)
	@echo "✓ Images pushed"

# Build and push everything
docker-all: docker-build docker-build-ui docker-push

# K8s deployment
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f ../deploy/k8s/namespace-swe.yaml
	kubectl apply -f ../deploy/k8s-new/
	@echo "✓ Deployed to Kubernetes"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -rf */gen
	@rm -rf $(PY_OUT)
	@rm -rf bin
	@echo "✓ Cleaned"

# Help
help:
	@echo "SWE AI Fleet Microservices - Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  gen                    - Generate all gRPC code (Go + Python)"
	@echo "  gen-go                 - Generate Go gRPC code only"
	@echo "  gen-py                 - Generate Python gRPC code only"
	@echo "  lint                   - Lint Go code"
	@echo "  fmt                    - Format Go code"
	@echo "  deps                   - Install Go dependencies"
	@echo "  build                  - Build all Go services"
	@echo "  test                   - Run all tests"
	@echo "  docker-build           - Build all Docker images"
	@echo "  docker-build-planning  - Build Planning service image"
	@echo "  docker-build-ui        - Build UI image"
	@echo "  docker-push            - Push all Docker images to registry"
	@echo "  docker-all             - Build and push all images"
	@echo "  k8s-deploy             - Deploy to Kubernetes"
	@echo "  clean                  - Clean generated files"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY               - Container registry (default: ghcr.io/underpass-ai/swe-fleet)"
	@echo "  VERSION                - Image version/tag (default: latest)"
	@echo "  CONTAINER_ENGINE       - Container tool: podman, buildah, nerdctl (auto-detected)"
	@echo ""
	@echo "Detected container engine: $(CONTAINER_ENGINE)"
	@echo "Build command: $(BUILD_CMD)"
	@echo "Push command: $(PUSH_CMD)"
