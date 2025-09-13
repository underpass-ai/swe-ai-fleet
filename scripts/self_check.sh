#!/usr/bin/env bash
set -euo pipefail

# Self-check runner for the local CRI-O stack
# Usage:
#   scripts/self_check.sh reset         # full reset: stop all, start+validate, then STOP ALL (default)
#   scripts/self_check.sh check         # start if needed, validate, LEAVE RUNNING
# Sequence (for check/reset-check):
# 1) Redis → 2) Neo4j → 3) vLLM → 4) Web → 5) Kong

# Non-interactive sudo to avoid hangs
# Prefer non-interactive sudo; fall back to interactive if needed
if sudo -n true >/dev/null 2>&1; then
  SUDO="sudo -n"
else
  SUDO="sudo"
fi

# Load .env if present
if [ -f ./.env ]; then
  set -a
  . ./.env
  set +a
fi

REDIS_PASSWORD="${REDIS_PASSWORD:-${REDIS_URL#*redis://:}}"
REDIS_PASSWORD="${REDIS_PASSWORD%%@*}"
REDIS_PASSWORD="${REDIS_PASSWORD:-swefleet-dev}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-swefleet-dev}"
VLLM_PORT="${PORT:-8000}"
WEB_PORT="${WEB_PORT:-8080}"

START_EPOCH=$(date +%s)
log() { printf "[%s +%ss] %s\n" "$(date +%H:%M:%S)" "$(( $(date +%s) - START_EPOCH ))" "$*"; }
pass() { printf "[%s +%ss] \033[32mPASS\033[0m %s\n" "$(date +%H:%M:%S)" "$(( $(date +%s) - START_EPOCH ))" "$*"; }
fail() { printf "[%s +%ss] \033[31mFAIL\033[0m %s\n" "$(date +%H:%M:%S)" "$(( $(date +%s) - START_EPOCH ))" "$*"; }

retry() { :; }

get_cid() {
  # get_cid <name>
  $SUDO crictl ps -a --name "$1" -q | head -n1 || true
}

wait_http_ok() {
  # wait_http_ok <url> <timeout_s> <attempts>
  local url="$1"; local timeout_s="$2"; local attempts="$3"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl -sf --max-time "$timeout_s" "$url" >/dev/null; then return 0; fi
    sleep 2
  done
  return 1
}

check_redis() {
  log "Starting Redis (if needed)"
  local step_start=$(date +%s)
  $SUDO bash scripts/redis_crio.sh start || { log "redis_crio start failed, attempting image pull and retry"; $SUDO crictl pull "${REDIS_IMAGE:-docker.io/library/redis:7-alpine}" || true; $SUDO bash scripts/redis_crio.sh start || return 1; }
  local cid; cid=$(get_cid redis)
  if [ -z "$cid" ]; then fail "Redis container not found"; return 1; fi
  log "Waiting for Redis to respond to PING"
  local i
  for i in $(seq 1 30); do
    if $SUDO crictl exec -i "$cid" sh -lc 'RP="'"$REDIS_PASSWORD"'"; if [ -n "$RP" ]; then redis-cli -a "$RP" PING; else redis-cli PING; fi' 2>/dev/null | grep -q PONG; then
      pass "Redis PING ($(( $(date +%s) - step_start ))s)"
      return 0
    fi
    sleep 1
  done
  $SUDO crictl logs "$cid" | tail -n 120 | sed -n '1,200p' || true
  fail "Redis did not respond to PING"
  return 1
}

check_neo4j() {
  log "Starting Neo4j (if needed)"
  local step_start=$(date +%s)
  $SUDO bash scripts/neo4j_crio.sh start || { log "neo4j_crio start failed, attempting image pull and retry"; $SUDO crictl pull "${NEO4J_IMAGE:-docker.io/neo4j:5}" || true; $SUDO bash scripts/neo4j_crio.sh start || return 1; }
  local cid; cid=$(get_cid neo4j)
  if [ -z "$cid" ]; then fail "Neo4j container not found"; return 1; fi
  log "Waiting for Neo4j HTTP at 127.0.0.1:7474"
  local i
  for i in $(seq 1 40); do
    # Accept 200/401/302 as alive
    code=$(curl -sS -u "neo4j:$NEO4J_PASSWORD" -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:7474/ || true)
    if [ "$code" = "200" ] || [ "$code" = "401" ] || [ "$code" = "302" ]; then
      pass "Neo4j HTTP alive (code $code) ($(( $(date +%s) - step_start ))s)"
      return 0
    fi
    sleep 2
  done
  $SUDO crictl logs "$cid" | tail -n 200 | sed -n '1,200p' || true
  fail "Neo4j did not become ready"
  return 1
}

check_vllm() {
  log "Starting vLLM (if needed)"
  local step_start=$(date +%s)
  $SUDO bash scripts/vllm_crio.sh start || true
  local cid; cid=$(get_cid vllm)
  if [ -z "$cid" ]; then fail "vLLM container not found"; return 1; fi
  log "Waiting for vLLM /v1/models at 127.0.0.1:${VLLM_PORT}"
  local i
  for i in $(seq 1 60); do
    if curl -sf --max-time 3 "http://127.0.0.1:${VLLM_PORT}/v1/models" >/dev/null; then
      pass "vLLM models API ($(( $(date +%s) - step_start ))s)"
      return 0
    fi
    sleep 2
    if [ $i -eq 20 ] || [ $i -eq 40 ]; then
      log "vLLM recent logs (tail 120)"
      $SUDO crictl logs "$cid" | tail -n 120 | sed -n '1,200p' || true
    fi
  done
  fail "vLLM did not become ready"
  return 1
}

ensure_kong_config() {
  local cfg="/home/ia/develop/swe-ai-fleet/deploy/podman/kong/kong.yml"
  if [ ! -f "$cfg" ]; then
    log "Creating minimal Kong declarative config at $cfg"
    mkdir -p "$(dirname "$cfg")"
    cat > "$cfg" <<'YAML'
_format_version: '3.0'
_transform: true
services:
  - name: web
    url: http://127.0.0.1:8080
    routes:
      - name: web
        paths: ["/api"]
  - name: vllm
    url: http://127.0.0.1:8000
    routes:
      - name: v1
        paths: ["/v1"]
YAML
  fi
}

check_web() {
  log "Starting Web (if needed)"
  local step_start=$(date +%s)
  export VLLM_ENDPOINT="http://127.0.0.1:${VLLM_PORT}"
  $SUDO bash scripts/web_crio.sh start || true
  local cid; cid=$(get_cid web)
  if [ -z "$cid" ]; then fail "Web container not found"; return 1; fi
  log "Waiting for Web /healthz at 127.0.0.1:${WEB_PORT}"
  if wait_http_ok "http://127.0.0.1:${WEB_PORT}/healthz" 3 60; then
    pass "Web healthz ($(( $(date +%s) - step_start ))s)"
    return 0
  fi
  $SUDO crictl logs "$cid" | tail -n 200 | sed -n '1,200p' || true
  fail "Web did not become ready"
  return 1
}

check_kong() {
  ensure_kong_config
  log "Starting Kong (if needed)"
  local step_start=$(date +%s)
  $SUDO bash scripts/kong_crio.sh start || true
  local cid; cid=$(get_cid kong)
  if [ -z "$cid" ]; then fail "Kong container not found"; return 1; fi
  log "Waiting for Kong to proxy /v1/models"
  if wait_http_ok "http://127.0.0.1:8081/v1/models" 3 60; then
    pass "Kong proxy to vLLM ($(( $(date +%s) - step_start ))s)"
    return 0
  fi
  $SUDO crictl logs "$cid" | tail -n 200 | sed -n '1,200p' || true
  fail "Kong did not become ready"
  return 1
}

stop_all() {
  log "Stopping all containers via crictl"
  # List all container IDs (fallback parsing if -q unsupported)
  cids=$($SUDO crictl ps -a -q 2>/dev/null || $SUDO crictl ps -a 2>/dev/null | awk 'NR>1 {print $1}')
  if [ -n "${cids:-}" ]; then
    for cid in $cids; do
      [ -z "$cid" ] && continue
      log "Stopping container: $cid"
      $SUDO crictl stop "$cid" || true
      $SUDO crictl rm -f "$cid" || true
    done
  fi

  log "Stopping all pods via crictl"
  # List all pod IDs (fallback parsing to first column)
  pids=$($SUDO crictl pods -q 2>/dev/null || $SUDO crictl pods 2>/dev/null | awk 'NR>1 {print $1}')
  if [ -n "${pids:-}" ]; then
    for pid in $pids; do
      [ -z "$pid" ] && continue
      log "Stopping pod: $pid"
      $SUDO crictl stopp "$pid" || true
      $SUDO crictl rmp -f "$pid" || true
    done
  fi
}

check_sequence() {
  # Sequential steps; abort on first failure
  check_redis || { fail "Redis step failed"; return 1; }
  check_neo4j || { fail "Neo4j step failed"; return 1; }
  check_vllm || { fail "vLLM step failed"; return 1; }
  check_web || { fail "Web step failed"; return 1; }
  check_kong || { fail "Kong step failed"; return 1; }
  log "All services are operative."
  return 0
}

main() {
  local cmd="${1:-reset}"
  case "$cmd" in
    check)
      check_sequence || exit 1
      ;;
    reset|*)
      stop_all || true
      check_sequence || { rc=$?; stop_all || true; exit "$rc"; }
      stop_all || true
      ;;
  esac
}

main "${1:-}"


