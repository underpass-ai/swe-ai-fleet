# make/e2e.mk — E2E test targets

.PHONY: e2e-run e2e-build e2e-build-test e2e-push e2e-push-test \
        e2e-build-push e2e-build-push-test \
        e2e-ephemeral-up e2e-ephemeral-down e2e-ephemeral-status

e2e-run: ## Run E2E tests sequentially (Kubernetes jobs)
	@bash e2e/run-e2e-tests.sh

e2e-build: ## Build all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) build

e2e-build-test: ## Build a specific E2E test image. Usage: make e2e-build-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-build-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) build --test $(TEST)

e2e-push: ## Push all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) push

e2e-push-test: ## Push a specific E2E test image. Usage: make e2e-push-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-push-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) push --test $(TEST)

e2e-build-push: ## Build and push all E2E test images
	@bash $(E2E_IMAGES_SCRIPT) build-push

e2e-build-push-test: ## Build and push a specific E2E test image. Usage: make e2e-build-push-test TEST=<test-directory>
	@if [ -z "$(TEST)" ]; then \
		echo "ERROR: TEST parameter is required"; \
		echo "Usage: make e2e-build-push-test TEST=<test-directory>"; \
		exit 1; \
	fi
	@bash $(E2E_IMAGES_SCRIPT) build-push --test $(TEST)

e2e-ephemeral-up: ## Deploy ephemeral E2E deps (mongo/postgres/kafka/rabbit/nats)
	@bash e2e/auxiliary/ephemeral-deps.sh up

e2e-ephemeral-down: ## Delete ephemeral E2E deps (mongo/postgres/kafka/rabbit/nats)
	@bash e2e/auxiliary/ephemeral-deps.sh down

e2e-ephemeral-status: ## Show ephemeral E2E deps status
	@bash e2e/auxiliary/ephemeral-deps.sh status
