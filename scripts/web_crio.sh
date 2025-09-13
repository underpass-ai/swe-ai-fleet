#!/usr/bin/env bash
set -euo pipefail

# FastAPI web under CRI-O using crictl (pod+container)
# Usage:
#   sudo bash scripts/web_crio.sh start   # create pod+container and start web server
#   sudo bash scripts/web_crio.sh logs    # tail logs
#   sudo bash scripts/web_crio.sh status  # show status
#   sudo bash scripts/web_crio.sh stop    # remove container and pod

IMAGE="${IMAGE:-localhost/swe-ai-fleet-web:local}"
STATE_DIR="${STATE_DIR:-/tmp/swe-web}"
POD_JSON="$STATE_DIR/web-pod.json"
CTR_JSON="$STATE_DIR/web-ctr.json"
POD_FILE="$STATE_DIR/pod.id"
CTR_FILE="$STATE_DIR/ctr.id"

PORT="${PORT:-8080}"
# Load .env if present
if [ -f ./.env ]; then
  set -a
  . ./.env
  set +a
fi

REDIS_URL="${REDIS_URL:-redis://:swefleet-dev@127.0.0.1:6379/0}"
NEO4J_URI="${NEO4J_URI:-bolt://127.0.0.1:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-swefleet-dev}"
VLLM_ENDPOINT="${VLLM_ENDPOINT:-}"
DEV_MODE="${DEV_MODE:-}"

mkdir -p "$STATE_DIR"

ensure_crictl() {
  if ! command -v crictl >/dev/null 2>&1; then echo "crictl not found" >&2; exit 1; fi
}

write_json() {
  cat >"$POD_JSON" <<JSON
{"metadata":{"name":"web","namespace":"default","uid":"web-uid"},
 "log_directory":"/tmp",
 "linux":{"security_context":{"namespace_options":{"network":2}}} }
JSON

  # Auto-enable dev mode if using local placeholder image
  if [ -z "$DEV_MODE" ] && [ "$IMAGE" = "localhost/swe-ai-fleet-web:local" ]; then
    DEV_MODE=1
  fi

  if [ "${DEV_MODE:-}" = "1" ]; then
    local dev_image="docker.io/library/python:3.13-slim"
    cat >"$CTR_JSON" <<JSON
{"metadata":{"name":"web"},
 "image":{"image":"$dev_image"},
 "log_path":"web.log",
 "mounts":[{"container_path":"/app","host_path":"/home/ia/develop/swe-ai-fleet","readonly":false}],
 "envs":[
   {"name":"PYTHONUNBUFFERED","value":"1"},
   {"name":"HOST","value":"0.0.0.0"},
   {"name":"PORT","value":"$PORT"},
   {"name":"REDIS_URL","value":"$REDIS_URL"},
   {"name":"NEO4J_URI","value":"$NEO4J_URI"},
   {"name":"NEO4J_USER","value":"$NEO4J_USER"},
   {"name":"NEO4J_PASSWORD","value":"$NEO4J_PASSWORD"}
   $( [ -n "$VLLM_ENDPOINT" ] && printf ',{"name":"VLLM_ENDPOINT","value":"%s"}' "$VLLM_ENDPOINT" )
 ],
 "command":["/bin/sh","-lc"],
 "args":["echo '[web] Updating pip...'; python -m pip install -U pip && \
           echo '[web] Installing app extras (web)...'; python -m pip install -e /app[web] && \
           echo '[web] Starting FastAPI server (uvicorn factory)...'; python -m uvicorn swe_ai_fleet.web.server:create_app --host 0.0.0.0 --port $PORT --factory --log-level info"],
 "port_mappings":[{"container_port":$PORT,"host_port":$PORT,"protocol":"TCP"}],
 "linux":{"security_context":{"privileged":false}} }
JSON
    export _WEB_IMAGE_TO_PULL="$dev_image"
  else
    cat >"$CTR_JSON" <<JSON
{"metadata":{"name":"web"},
 "image":{"image":"$IMAGE"},
 "log_path":"web.log",
 "envs":[
   {"name":"HOST","value":"0.0.0.0"},
   {"name":"PORT","value":"$PORT"},
   {"name":"REDIS_URL","value":"$REDIS_URL"},
   {"name":"NEO4J_URI","value":"$NEO4J_URI"},
   {"name":"NEO4J_USER","value":"$NEO4J_USER"},
   {"name":"NEO4J_PASSWORD","value":"$NEO4J_PASSWORD"}
   $( [ -n "$VLLM_ENDPOINT" ] && printf ',{"name":"VLLM_ENDPOINT","value":"%s"}' "$VLLM_ENDPOINT" )
 ],
 "port_mappings":[{"container_port":$PORT,"host_port":$PORT,"protocol":"TCP"}],
 "linux":{"security_context":{"privileged":false}} }
JSON
    export _WEB_IMAGE_TO_PULL="$IMAGE"
  fi
}

start() {
  ensure_crictl
  write_json
  # Pull if not present (use computed image var)
  if ! crictl images | awk '{print $1":"$2}' | grep -q "$(echo "$_WEB_IMAGE_TO_PULL" | awk -F: '{print $1}')"; then
    crictl pull "$_WEB_IMAGE_TO_PULL" || true
  fi
  POD_ID=$(crictl runp "$POD_JSON")
  echo "$POD_ID" >"$POD_FILE"
  CID=$(crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON")
  echo "$CID" >"$CTR_FILE"
  crictl start "$CID"
  echo "Started: POD_ID=$POD_ID CID=$CID"
}

logs() {
  ensure_crictl
  CID=$(cat "$CTR_FILE" 2>/dev/null || true)
  if [ -z "$CID" ]; then echo "No container id" >&2; exit 1; fi
  crictl logs -f "$CID"
}

status() {
  ensure_crictl
  CID=${CID:-$(cat "$CTR_FILE" 2>/dev/null || true)}
  POD_ID=${POD_ID:-$(cat "$POD_FILE" 2>/dev/null || true)}
  echo "POD_ID=${POD_ID:-}"; echo "CID=${CID:-}"
  crictl ps | grep -E "web|$CID" || true
}

stop() {
  ensure_crictl
  CID=$(cat "$CTR_FILE" 2>/dev/null || true)
  POD_ID=$(cat "$POD_FILE" 2>/dev/null || true)
  if [ -n "${CID:-}" ]; then crictl rm -f "$CID" || true; rm -f "$CTR_FILE"; fi
  if [ -n "${POD_ID:-}" ]; then crictl rmp -f "$POD_ID" || true; rm -f "$POD_FILE"; fi
  echo "Stopped web pod and container."
}

case "${1:-}" in
  start) start ;;
  logs) logs ;;
  status) status ;;
  stop) stop ;;
  *) echo "Usage: $0 {start|logs|status|stop}" >&2; exit 2 ;;
esac


