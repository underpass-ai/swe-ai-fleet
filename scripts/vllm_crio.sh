#!/usr/bin/env bash
set -euo pipefail

# vLLM OpenAI server under CRI-O with NVIDIA CDI GPUs
# Usage:
#   sudo bash scripts/vllm_crio.sh start   # create pod+container and start server
#   sudo bash scripts/vllm_crio.sh logs    # tail logs
#   sudo bash scripts/vllm_crio.sh status  # show status and probe endpoint
#   sudo bash scripts/vllm_crio.sh stop    # remove container and pod

IMAGE="${IMAGE:-docker.io/vllm/vllm-openai:latest}"
MODEL="${MODEL:-TinyLlama/TinyLlama-1.1B-Chat-v1.0}"
TP="${TP:-2}"
PORT="${PORT:-8000}"
CUDA_VISIBLE_DEVICES_DEFAULT="${CUDA_VISIBLE_DEVICES:-0,1}"

STATE_DIR="${STATE_DIR:-/tmp}"
POD_FILE="$STATE_DIR/vllm.pod"
CTR_FILE="$STATE_DIR/vllm.ctr"
POD_JSON="$STATE_DIR/vllm-pod.json"
CTR_JSON="$STATE_DIR/vllm-ctr.json"

ensure_crictl() {
  if ! command -v crictl >/dev/null 2>&1; then
    echo "crictl not found" >&2; exit 1
  fi
}

write_json() {
  cat >"$POD_JSON" <<JSON
{
  "metadata": {"name": "vllm-openai", "namespace": "default", "uid": "vllm-openai-uid"},
  "log_directory": "/tmp",
  "port_mappings": [
    {"container_port": $PORT, "host_port": $PORT, "protocol": 0}
  ],
  "linux": { "cgroup_parent": "system.slice" }
}
JSON

  cat >"$CTR_JSON" <<JSON
{
  "metadata": {"name": "vllm"},
  "image": {"image": "$IMAGE"},
  "args": ["--model","$MODEL","--tensor-parallel-size","$TP","--gpu-memory-utilization","0.85","--port","$PORT"],
  "log_path": "vllm-openai.log",
  "envs": [
    {"name":"HF_HOME","value":"/root/.cache/huggingface"},
    {"name":"VLLM_DEVICE","value":"cuda"},
    {"name":"NVIDIA_VISIBLE_DEVICES","value":"all"},
    {"name":"NVIDIA_DRIVER_CAPABILITIES","value":"compute,utility"},
    {"name":"CUDA_VISIBLE_DEVICES","value":"$CUDA_VISIBLE_DEVICES_DEFAULT"}
  ],
  "linux": { "security_context": { "privileged": false } },
  "annotations": { "io.kubernetes.cri-o.Devices": "nvidia.com/gpu=all" }
}
JSON
}

start() {
  ensure_crictl
  write_json
  # Pull image if not present
  if ! crictl images | grep -q "$(echo "$IMAGE" | awk -F: '{print $1}')"; then
    crictl pull "$IMAGE"
  fi
  POD_ID=$(crictl runp "$POD_JSON")
  echo "$POD_ID" >"$POD_FILE"
  CID=$(crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON")
  echo "$CID" >"$CTR_FILE"
  crictl start "$CID"
  echo "Started: POD_ID=$POD_ID CID=$CID"
  sleep 8
  status
}

logs() {
  ensure_crictl
  if [ ! -s "$CTR_FILE" ]; then echo "No container file at $CTR_FILE" >&2; exit 1; fi
  CID=$(cat "$CTR_FILE")
  crictl logs -f "$CID"
}

status() {
  ensure_crictl
  CID=${CID:-$(cat "$CTR_FILE" 2>/dev/null || true)}
  POD_ID=${POD_ID:-$(cat "$POD_FILE" 2>/dev/null || true)}
  echo "POD_ID=${POD_ID:-}"; echo "CID=${CID:-}"
  crictl ps | grep -E "vllm|$CID" || true
  if command -v curl >/dev/null 2>&1; then
    echo "--- probe /v1/models ---"
    curl -sf "http://127.0.0.1:${PORT}/v1/models" | sed -n '1,40p' || true
  fi
}

stop() {
  ensure_crictl
  CID=$(cat "$CTR_FILE" 2>/dev/null || true)
  POD_ID=$(cat "$POD_FILE" 2>/dev/null || true)
  if [ -n "${CID:-}" ]; then crictl rm -f "$CID" || true; rm -f "$CTR_FILE"; fi
  if [ -n "${POD_ID:-}" ]; then crictl rmp -f "$POD_ID" || true; rm -f "$POD_FILE"; fi
  echo "Stopped vLLM pod and container."
}

cmd="${1:-start}"
case "$cmd" in
  start) start ;;
  logs) logs ;;
  status) status ;;
  stop) stop ;;
  *) echo "Usage: $0 {start|logs|status|stop}" >&2; exit 2 ;;
esac





