REDIS_PASSWORD ?= swefleet-dev

redis-up:
	docker compose -f deploy/docker/redis/docker-compose.yml --env-file .env.dev up -d

redis-down:
	docker compose -f deploy/docker/redis/docker-compose.yml --env-file .env.dev down

redis-cli:
	docker exec -it swe-ai-fleet-redis redis-cli -a $(REDIS_PASSWORD) PING

insight:
	@echo "Open http://localhost:5540 and add database: $(REDIS_URL)"

docs-install:
	python -m pip install -r docs/requirements.txt

docs-build:
	mkdocs build --strict

docs-serve:
	mkdocs serve -a 0.0.0.0:8000
