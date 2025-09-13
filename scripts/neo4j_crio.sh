#!/usr/bin/env bash
set -euo pipefail

# Neo4j on CRI-O. Honors .env (NEO4J_PASSWORD). Defaults to neo4j/test.
# Usage: sudo bash scripts/neo4j_crio.sh {start|status|logs|stop}

STATE_DIR="${STATE_DIR:-/tmp/neo4j-crio}"
POD_JSON="$STATE_DIR/neo4j-pod.json"
CTR_JSON="$STATE_DIR/neo4j-ctr.json"
POD_FILE="$STATE_DIR/pod.id"
CTR_FILE="$STATE_DIR/ctr.id"

mkdir -p "$STATE_DIR"

ensure_crictl() { command -v crictl >/dev/null 2>&1 || { echo "crictl not found" >&2; exit 1; }; }
load_env() { if [ -f ./.env ]; then set -a; . ./.env; set +a; fi; }

write_json() {
  local pw="${NEO4J_PASSWORD:-test}"
  cat >"$POD_JSON" <<JSON
{"metadata":{"name":"neo4j","namespace":"default","uid":"neo4j-uid"},
 "log_directory":"/tmp",
 "linux":{"security_context":{"namespace_options":{"network":2}}}}
JSON

  cat >"$CTR_JSON" <<JSON
{"metadata":{"name":"neo4j"},
 "image":{"image":"docker.io/neo4j:5"},
 "envs":[
   {"name":"NEO4J_AUTH","value":"neo4j/${pw}"},
   {"name":"NEO4J_server_default__listen__address","value":"0.0.0.0"},
   {"name":"NEO4J_server_http__listen__address","value":"0.0.0.0:7474"},
   {"name":"NEO4J_server_bolt__listen__address","value":"0.0.0.0:7687"}
 ],
 "log_path":"neo4j.log",
 "linux":{"security_context":{"privileged":false}}}
JSON
}

start() {
  ensure_crictl; load_env; write_json
  POD_ID=$(crictl runp "$POD_JSON"); echo "$POD_ID" >"$POD_FILE"
  CID=$(crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON"); echo "$CID" >"$CTR_FILE"
  crictl start "$CID"
  echo "Started Neo4j: POD=$POD_ID CID=$CID"
}

status() { ensure_crictl; crictl ps | grep -E "neo4j|$(cat "$CTR_FILE" 2>/dev/null || true)" || true; }
logs() { ensure_crictl; crictl logs -f "$(cat "$CTR_FILE")"; }
stop() {
  ensure_crictl
  [ -f "$CTR_FILE" ] && crictl rm -f "$(cat "$CTR_FILE")" || true
  [ -f "$POD_FILE" ] && crictl rmp -f "$(cat "$POD_FILE")" || true
  rm -f "$CTR_FILE" "$POD_FILE"
  echo "Stopped Neo4j."
}

case "${1:-start}" in
  start) start ;;
  status) status ;;
  logs) logs ;;
  stop) stop ;;
  *) echo "Usage: $0 {start|status|logs|stop}" >&2; exit 2 ;;
esac


