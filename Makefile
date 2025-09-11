REDIS_PASSWORD ?= swefleet-dev

redis-up:
	docker compose -f deploy/docker/redis/docker-compose.yml --env-file .env.dev up -d

redis-down:
	docker compose -f deploy/docker/redis/docker-compose.yml --env-file .env.dev down

redis-cli:
	docker exec -it swe-ai-fleet-redis redis-cli -a $(REDIS_PASSWORD) PING

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

