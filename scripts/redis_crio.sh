#!/usr/bin/env bash
set -euo pipefail

# Redis on CRI-O using crictl. Honors .env (REDIS_PASSWORD optional).
# Usage: sudo bash scripts/redis_crio.sh {start|status|logs|stop}

STATE_DIR="${STATE_DIR:-/tmp/redis-crio}"
POD_JSON="$STATE_DIR/redis-pod.json"
CTR_JSON="$STATE_DIR/redis-ctr.json"
POD_FILE="$STATE_DIR/pod.id"
CTR_FILE="$STATE_DIR/ctr.id"

mkdir -p "$STATE_DIR"

ensure_crictl() {
  command -v crictl >/dev/null 2>&1 || { echo "crictl not found" >&2; exit 1; }
}

load_env() {
  if [ -f ./.env ]; then
    set -a; . ./.env; set +a
  fi
}

write_json() {
  local requirepass_args=()
  if [ -n "${REDIS_PASSWORD:-}" ]; then
    requirepass_args=("--requirepass" "$REDIS_PASSWORD")
  fi

  cat >"$POD_JSON" <<JSON
{"metadata":{"name":"redis","namespace":"default","uid":"redis-uid"},
 "log_directory":"/tmp",
 "linux":{"security_context":{"namespace_options":{"network":2}}}}
JSON

  cat >"$CTR_JSON" <<JSON
{"metadata":{"name":"redis"},
 "image":{"image":"docker.io/library/redis:7-alpine"},
 "command":["redis-server"],
 "args":["--appendonly","no","--save","","--bind","0.0.0.0","--protected-mode","no","--maxmemory-policy","allkeys-lru"],
 "log_path":"redis.log",
 "linux":{"security_context":{"privileged":false}}}
JSON

  # Inject requirepass if set
  if [ -n "${REDIS_PASSWORD:-}" ]; then
    tmp=$(mktemp)
    jq '.args |= . + ["--requirepass","'"$REDIS_PASSWORD"'"]' "$CTR_JSON" > "$tmp" && mv "$tmp" "$CTR_JSON"
  fi
}

start() {
  ensure_crictl; load_env; write_json
  POD_ID=$(crictl runp "$POD_JSON"); echo "$POD_ID" >"$POD_FILE"
  CID=$(crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON"); echo "$CID" >"$CTR_FILE"
  crictl start "$CID"
  echo "Started Redis: POD=$POD_ID CID=$CID"
}

status() {
  ensure_crictl
  CID=${CID:-$(cat "$CTR_FILE" 2>/dev/null || true)}
  POD_ID=${POD_ID:-$(cat "$POD_FILE" 2>/dev/null || true)}
  echo "POD_ID=${POD_ID:-}"; echo "CID=${CID:-}"
  crictl ps | grep -E "redis|$CID" || true
}

logs() {
  ensure_crictl
  crictl logs -f "$(cat "$CTR_FILE")"
}

stop() {
  ensure_crictl
  [ -f "$CTR_FILE" ] && crictl rm -f "$(cat "$CTR_FILE")" || true
  [ -f "$POD_FILE" ] && crictl rmp -f "$(cat "$POD_FILE")" || true
  rm -f "$CTR_FILE" "$POD_FILE"
  echo "Stopped Redis."
}

case "${1:-start}" in
  start) start ;;
  status) status ;;
  logs) logs ;;
  stop) stop ;;
  *) echo "Usage: $0 {start|status|logs|stop}" >&2; exit 2 ;;
esac


