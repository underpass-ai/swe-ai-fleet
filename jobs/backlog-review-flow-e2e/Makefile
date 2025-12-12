# Makefile for Backlog Review Flow E2E Test Job

IMAGE_NAME := registry.underpassai.com/swe-ai-fleet/backlog-review-flow-e2e
IMAGE_TAG := v1.0.0
NAMESPACE := swe-ai-fleet
JOB_NAME := backlog-review-flow-e2e

.PHONY: help build build-push deploy logs clean delete

help:
	@echo "Backlog Review Flow E2E Test Job"
	@echo ""
	@echo "Available targets:"
	@echo "  build        - Build Docker image locally"
	@echo "  build-push   - Build and push Docker image to registry"
	@echo "  deploy       - Deploy Kubernetes Job"
	@echo "  logs         - View job logs"
	@echo "  status       - Check job status"
	@echo "  clean        - Delete completed job"
	@echo "  delete       - Delete job and related resources"
	@echo ""

build:
	@echo "Building Docker image..."
	@if [ -f "Dockerfile" ]; then \
		# Running from job directory - need to find root \
		ROOT_DIR=$$(cd ../.. && pwd); \
		echo "Building from job directory, using root: $$ROOT_DIR"; \
		podman build -t $(IMAGE_NAME):$(IMAGE_TAG) \
			-f $$(pwd)/Dockerfile \
			--build-arg BUILDKIT_INLINE_CACHE=1 \
			$$ROOT_DIR; \
	else \
		# Running from root directory \
		echo "Building from root directory"; \
		podman build -t $(IMAGE_NAME):$(IMAGE_TAG) \
			-f jobs/backlog-review-flow-e2e/Dockerfile \
			--build-arg BUILDKIT_INLINE_CACHE=1 \
			.; \
	fi

build-push: build
	@echo "Pushing Docker image to registry..."
	podman push $(IMAGE_NAME):$(IMAGE_TAG)

deploy:
	@echo "Deploying Kubernetes Job..."
	@if [ -f "job.yaml" ]; then \
		kubectl apply -f job.yaml; \
	else \
		kubectl apply -f jobs/backlog-review-flow-e2e/job.yaml; \
	fi
	@echo ""
	@echo "Job deployed. Watch status with: make status"
	@echo "View logs with: make logs"

logs:
	@echo "Fetching logs from job..."
	@POD_NAME=$$(kubectl get pods -n $(NAMESPACE) -l app=$(JOB_NAME) --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD_NAME" ]; then \
		echo "No pod found for job $(JOB_NAME)"; \
		exit 1; \
	fi; \
	kubectl logs -n $(NAMESPACE) $$POD_NAME -f

status:
	@echo "Job status:"
	@kubectl get job -n $(NAMESPACE) $(JOB_NAME) || echo "Job not found"
	@echo ""
	@echo "Pod status:"
	@kubectl get pods -n $(NAMESPACE) -l app=$(JOB_NAME)

clean:
	@echo "Deleting completed job..."
	@kubectl delete job -n $(NAMESPACE) $(JOB_NAME) --ignore-not-found=true
	@echo "Job deleted"

delete: clean
	@echo "Deleting ServiceAccount, Role, and RoleBinding..."
	@kubectl delete serviceaccount -n $(NAMESPACE) e2e-test-runner --ignore-not-found=true
	@kubectl delete role -n $(NAMESPACE) e2e-test-runner --ignore-not-found=true
	@kubectl delete rolebinding -n $(NAMESPACE) e2e-test-runner --ignore-not-found=true
	@echo "All resources deleted"





