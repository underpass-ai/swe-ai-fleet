#!/usr/bin/env bash
set -euo pipefail
PASS="${REDIS_PASSWORD:-swefleet-dev}"
echo "PING" | docker exec -i swe-ai-fleet-redis redis-cli -a "$PASS"
docker exec -i swe-ai-fleet-redis redis-cli -a "$PASS" SET fleet:smoke "ok"
docker exec -i swe-ai-fleet-redis redis-cli -a "$PASS" GET fleet:smoke
