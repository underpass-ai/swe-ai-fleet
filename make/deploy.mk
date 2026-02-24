# make/deploy.mk — Deployment, cluster ops, runner images, and prune targets

.PHONY: deploy-build deploy-build-no-cache deploy deploy-service \
        list-services persistence-clean cluster-clear \
        service-image-prune e2e-image-prune \
        runner-list runner-build runner-push runner-build-push

deploy-build: ## Build+push all services using cache (no deploy)
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --cache --build-only

deploy-build-no-cache: ## Build+push all services without cache (no deploy)
	@VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all --no-cache --build-only

deploy: ## Single deploy command for all services. Optional: NO_CACHE=1 SKIP_BUILD=1 RESET_NATS=1 WITH_E2E=1
	@opts="--cache"; \
	if [ "$${NO_CACHE:-0}" = "1" ]; then opts="--no-cache"; fi; \
	if [ "$${SKIP_BUILD:-0}" = "1" ]; then opts="$$opts --skip-build"; fi; \
	if [ "$${RESET_NATS:-0}" = "1" ]; then opts="$$opts --reset-nats"; fi; \
	if [ "$${WITH_E2E:-0}" = "1" ]; then opts="$$opts --with-e2e"; fi; \
	VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) all $$opts

deploy-service: ## Deploy one service. Usage: make deploy-service SERVICE=<name> [NO_CACHE=1] [SKIP_BUILD=1] [RESET_NATS=1]
	@if [ -z "$(SERVICE)" ]; then \
		echo "ERROR: SERVICE parameter is required"; \
		echo "Usage: make deploy-service SERVICE=<service-name>"; \
		echo ""; \
		bash $(INFRA_DEPLOY_SCRIPT) list-services; \
		exit 1; \
	fi
	@opts="--cache"; \
	if [ "$${NO_CACHE:-0}" = "1" ]; then opts="--no-cache"; fi; \
	if [ "$${SKIP_BUILD:-0}" = "1" ]; then opts="$$opts --skip-build"; fi; \
	if [ "$${RESET_NATS:-0}" = "1" ]; then opts="$$opts --reset-nats"; fi; \
	VLLM_SERVER_IMAGE="$(VLLM_SERVER_IMAGE)" bash $(INFRA_DEPLOY_SCRIPT) service $(SERVICE) $$opts

list-services: ## List all available services for deployment
	@bash $(INFRA_DEPLOY_SCRIPT) list-services

persistence-clean: ## Full persistence cleanup: purge NATS streams + clean Neo4j and Valkey
	@bash $(INFRA_PERSISTENCE_CLEAN_SCRIPT)

cluster-clear: ## Clear jobs + Valkey/NATS/Neo4j + MinIO workspace buckets
	@bash $(INFRA_CLUSTER_CLEAR_SCRIPT)

service-image-prune: ## Delete old service image tags, keeping latest N tags per image (default KEEP=2)
	@KEEP="$${KEEP:-2}" DRY_RUN="$${DRY_RUN:-0}" REGISTRY="$${REGISTRY:-registry.underpassai.com/swe-ai-fleet}" bash $(INFRA_SERVICE_IMAGE_PRUNE_SCRIPT)

e2e-image-prune: ## Delete old E2E job image tags, keeping latest N tags per image (default KEEP=2)
	@KEEP="$${KEEP:-2}" DRY_RUN="$${DRY_RUN:-0}" REGISTRY="$${REGISTRY:-registry.underpassai.com/swe-ai-fleet}" bash $(E2E_IMAGE_PRUNE_SCRIPT)

runner-list: ## List workspace runner image profiles and tags
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) list --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0}

runner-build: ## Build runner images. Usage: make runner-build PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) build --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${NO_CACHE:+--no-cache} $${TAG_LATEST:+--tag-latest}

runner-push: ## Push runner images. Usage: make runner-push PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) push --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${TAG_LATEST:+--tag-latest}

runner-build-push: ## Build and push runner images. Usage: make runner-build-push PROFILE=all TAG=v0.1.0
	@bash $(WORKSPACE_RUNNER_IMAGES_SCRIPT) build-push --profile $${PROFILE:-all} --tag $${TAG:-v0.1.0} $${NO_CACHE:+--no-cache} $${TAG_LATEST:+--tag-latest}
