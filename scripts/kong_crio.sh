#!/usr/bin/env bash
set -euo pipefail

# Kong Gateway (DB-less) on CRI-O. Uses deploy/podman/kong/kong.yml.
# Usage: sudo bash scripts/kong_crio.sh {start|status|logs|stop}

STATE_DIR="${STATE_DIR:-/tmp/kong-crio}"
POD_JSON="$STATE_DIR/kong-pod.json"
CTR_JSON="$STATE_DIR/kong-ctr.json"
POD_FILE="$STATE_DIR/pod.id"
CTR_FILE="$STATE_DIR/ctr.id"

mkdir -p "$STATE_DIR"

ensure_crictl() { command -v crictl >/dev/null 2>&1 || { echo "crictl not found" >&2; exit 1; }; }

write_json() {
  cat >"$POD_JSON" <<JSON
{"metadata":{"name":"kong","namespace":"default","uid":"kong-uid"},
 "log_directory":"/tmp",
 "linux":{"security_context":{"namespace_options":{"network":2}}}}
JSON
  local cfg="/home/ia/develop/swe-ai-fleet/deploy/podman/kong/kong.yml"
  cat >"$CTR_JSON" <<JSON
{"metadata":{"name":"kong"},
 "image":{"image":"docker.io/kong/kong-gateway:3.6"},
 "log_path":"kong.log",
 "envs":[
   {"name":"KONG_DATABASE","value":"off"},
   {"name":"KONG_DECLARATIVE_CONFIG","value":"/kong/declarative/kong.yml"},
   {"name":"KONG_PROXY_LISTEN","value":"0.0.0.0:8081"}
 ],
 "mounts":[{"container_path":"/kong/declarative/kong.yml","host_path":"${cfg}","readonly":true}],
 "port_mappings":[{"container_port":8081,"host_port":8081,"protocol":"TCP"}],
 "linux":{"security_context":{"privileged":false}}}
JSON
}

start() {
  ensure_crictl; write_json
  # Pull kong image if needed
  if ! crictl images | awk '{print $1":"$2}' | grep -q "docker.io/kong/kong-gateway"; then
    crictl pull docker.io/kong/kong-gateway:3.6 || true
  fi
  POD_ID=$(crictl runp "$POD_JSON"); echo "$POD_ID" >"$POD_FILE"
  CID=$(crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON"); echo "$CID" >"$CTR_FILE"
  crictl start "$CID"
  echo "Started Kong: POD=$POD_ID CID=$CID"
}

status() { ensure_crictl; crictl ps | grep -E "kong|$(cat "$CTR_FILE" 2>/dev/null || true)" || true; }
logs() { ensure_crictl; crictl logs -f "$(cat "$CTR_FILE")"; }
stop() {
  ensure_crictl
  [ -f "$CTR_FILE" ] && crictl rm -f "$(cat "$CTR_FILE")" || true
  [ -f "$POD_FILE" ] && crictl rmp -f "$(cat "$POD_FILE")" || true
  rm -f "$CTR_FILE" "$POD_FILE"
  echo "Stopped Kong."
}

case "${1:-start}" in
  start) start ;;
  status) status ;;
  logs) logs ;;
  stop) stop ;;
  *) echo "Usage: $0 {start|status|logs|stop}" >&2; exit 2 ;;
esac


