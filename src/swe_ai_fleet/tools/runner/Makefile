# Container build variables
USER_UID ?= 1001
USER_GID ?= 1001
IMAGE_NAME ?= localhost/swe-ai-fleet-runner
CONTAINERFILE ?= Containerfile
TAG ?= latest
REGISTRY ?= localhost

# Build the container image
build:
	podman build --format docker \
		--build-arg USER_UID=$(USER_UID) \
		--build-arg USER_GID=$(USER_GID) \
		-t $(IMAGE_NAME):$(TAG) -f $(CONTAINERFILE) .

# Run the container interactively for testing
run:
	podman run --rm -it \
		-v $(PWD)/test-workspace:/workspace:Z \
		-v /run/podman/podman.sock:/var/run/docker.sock:Z \
		-e TASK=unit -e LANG=python \
		$(IMAGE_NAME):$(TAG) /bin/bash -l

# Run a specific task (example: make task TASK=unit LANG=python)
task:
	podman run --rm \
		-v $(PWD)/test-workspace:/workspace:Z \
		-v /run/podman/podman.sock:/var/run/docker.sock:Z \
		-e TASK=$(TASK) -e LANG=$(LANG) \
		$(IMAGE_NAME):$(TAG) /bin/bash -lc agent-task

# Tag image for registry
tag:
	podman tag $(IMAGE_NAME):$(TAG) $(REGISTRY)/$(IMAGE_NAME):$(TAG)

# Push to registry
push: tag
	podman push $(REGISTRY)/$(IMAGE_NAME):$(TAG)

# Clean up local images
clean:
	podman rmi $(IMAGE_NAME):$(TAG) || true
	podman rmi $(REGISTRY)/$(IMAGE_NAME):$(TAG) || true

# Show image info
info:
	podman images $(IMAGE_NAME):$(TAG)
	podman inspect $(IMAGE_NAME):$(TAG) | jq '.[0].Config.Labels'

# Help
help:
	@echo "Available targets:"
	@echo "  build    - Build the container image"
	@echo "  run      - Run container interactively"
	@echo "  task     - Run specific task (TASK=unit LANG=python)"
	@echo "  tag      - Tag image for registry"
	@echo "  push     - Push image to registry"
	@echo "  clean    - Remove local images"
	@echo "  info     - Show image information"
	@echo "  help     - Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  USER_UID=$(USER_UID)"
	@echo "  USER_GID=$(USER_GID)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  TAG=$(TAG)"
	@echo "  REGISTRY=$(REGISTRY)"

.PHONY: build run task tag push clean info help
