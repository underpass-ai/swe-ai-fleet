REDIS_PASSWORD ?= swefleet-dev
WEB_IMG ?= localhost/swe-ai-fleet-web:local
NET ?= swe-net

# ============================================================================
# Development Targets
# ============================================================================
.PHONY: install-deps

install-deps:  ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	@pip install --upgrade pip
	@pip install -e ".[grpc,dev]"
	@echo "✅ Dependencies installed"

# ============================================================================
# Testing Targets
# ============================================================================
.PHONY: test test-unit test-integration test-e2e test-coverage test-all

test: test-unit  ## Run unit tests (default)

test-unit:  ## Run unit tests with protobuf generation
	@bash scripts/test/unit.sh

test-integration:  ## Run integration tests with Podman
	@bash scripts/test/integration.sh

test-e2e:  ## Run end-to-end tests
	@bash scripts/test/e2e.sh

test-coverage:  ## Run unit tests with coverage report
	@bash scripts/test/coverage.sh

test-all:  ## Run all test suites (unit + integration + e2e)
	@bash scripts/test/all.sh

# ============================================================================
# Infrastructure Targets
# ============================================================================
.PHONY: web-build web-up web-down web-logs

web-build:
	@echo "Use CRI-O scripts for containers; web-build via Containerfile removed (no Podman)."

web-up:
	@echo "Use CRI-O: sudo bash scripts/web_crio.sh start"

web-down:
	@echo "Use CRI-O: sudo bash scripts/web_crio.sh stop"

web-logs:
	@echo "Use CRI-O: sudo bash scripts/web_crio.sh logs"

.PHONY: net-create net-rm

net-create:
	@echo "Network management is runtime-specific; for CRI-O use host networking in pod JSON."

net-rm:
	@echo "Network removal not applicable for CRI-O hostNetwork manifests."

.PHONY: redis-up-net neo4j-up-net vllm-up-net web-up-net web-down-net

redis-up-net:
	@echo "Use CRI-O: see deploy/crio/README.md for crictl runp/create/start of Redis."

neo4j-up-net:
	@echo "Use CRI-O: see deploy/crio/README.md for crictl runp/create/start of Neo4j."

vllm-up-net:
	@echo "Use CRI-O with GPU (runtime nvidia): see deploy/crio/README.md."

web-up-net:
	@echo "Use CRI-O script: sudo bash scripts/web_crio.sh start"

web-down-net:
	@echo "Use CRI-O script: sudo bash scripts/web_crio.sh stop"

.PHONY: gw-build gw-up gw-down gw-logs

gw-build:
	@echo "Gateway via CRI-O only; use a Pod manifest or run Kong with crictl."

gw-up:
	@echo "Use CRI-O: run Kong with crictl using a Pod+Container JSON."

gw-down:
	@echo "Use CRI-O: stop Kong via crictl."

gw-logs:
	@echo "Use CRI-O: crictl logs <kong-container-id>."

.PHONY: web-crio-start web-crio-logs web-crio-status web-crio-stop

web-crio-start:
	sudo bash scripts/web_crio.sh start

web-crio-logs:
	sudo bash scripts/web_crio.sh logs

web-crio-status:
	sudo bash scripts/web_crio.sh status

web-crio-stop:
	sudo bash scripts/web_crio.sh stop

redis-up:
	@echo "Use CRI-O manifests; docker compose targets removed."

redis-down:
	@echo "Use CRI-O manifests; docker compose targets removed."

redis-cli:
	@echo "Use redis-cli against localhost:6379 with password; container name not managed here."

insight:
	@echo "Open http://localhost:5540 and add database: $(REDIS_URL)"

# Ray GPU smoke tests (requires local Python with ray installed)
ray-smoke:
	python tests/ray/ray_gpu_smoke.py

ray-multi-gpu-smoke:
	python tests/ray/ray_multi_gpu_smoke.py

ray-gemm:
	python tests/ray/ray_gpu_gemm_bench.py

ray-stress:
	python tests/ray/ray_gpu_stress.py

