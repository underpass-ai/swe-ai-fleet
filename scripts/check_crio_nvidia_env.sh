#!/usr/bin/env bash

# Check NVIDIA + CRI-O/container environment (read-only by default)
#
# Usage:
#   ./scripts/check_crio_nvidia_env.sh [--smoke-crio] [--lines N]
#   ./scripts/check_crio_nvidia_env.sh --regen-cdi-no-dri   # (writes /etc/cdi/nvidia.yaml; requires sudo)
#   ./scripts/check_crio_nvidia_env.sh --check-services     # (vLLM, Redis, Neo4j quick checks)
#
# Notes:
# - Default run is read-only diagnostics. Smoke tests are opt-in.
# - Some sections use sudo for read-only system info (journald, crictl info, storage), if available.

set -uo pipefail

SMOKE_CRIO=0
REGEN_CDI_NO_DRI=0
TAIL_LINES=${LINES:-200}
CHECK_SERVICES=0

# Service params (override via env)
VLLM_PORT=${VLLM_PORT:-8000}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_PASSWORD=${REDIS_PASSWORD:-swefleet-dev}
NEO4J_HTTP_PORT=${NEO4J_HTTP_PORT:-7474}
NEO4J_BOLT_PORT=${NEO4J_BOLT_PORT:-7687}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-swefleet-dev}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke-crio) SMOKE_CRIO=1; shift ;;
    --regen-cdi-no-dri) REGEN_CDI_NO_DRI=1; shift ;;
    --check-services) CHECK_SERVICES=1; shift ;;
    --lines) TAIL_LINES="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--smoke-crio] [--regen-cdi-no-dri] [--check-services] [--lines N]"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

is_root() { [[ "$(id -u)" -eq 0 ]]; }

have() { command -v "$1" >/dev/null 2>&1; }

run() {
  echo "+ $*"; "$@" 2>&1 || true
}

sudo_run() {
  if is_root; then run "$@"; else if have sudo; then run sudo "$@"; else run "$@"; fi; fi
}

header() {
  echo; echo "=== $* ==="; }

header "1) GPU / Driver (host)"
run nvidia-smi | sed -n "1,50p"
run sh -c 'modinfo nvidia | grep -E "filename|version|vermagic"'
run sh -c 'cat /proc/driver/nvidia/version'
run sh -c 'ls -l /dev/nvidia* /dev/dri 2>/dev/null'

header "2) NVIDIA Container Toolkit & CDI"
run nvidia-container-cli -V
run sh -c 'nvidia-container-cli info 2>/dev/null | sed -n "1,120p"'
run nvidia-ctk --version
run nvidia-ctk cdi list
run sh -c 'ls -l /etc/cdi 2>/dev/null'
run sh -c 'sed -n "1,200p" /etc/cdi/nvidia.yaml 2>/dev/null'
run sh -c 'grep -n "/dev/dri" /etc/cdi/nvidia.yaml 2>/dev/null'
run sh -c 'command -v nvidia-cdi-hook >/dev/null 2>&1 && nvidia-cdi-hook --version || true'

header "3) CRI-O / crictl"
run crio --version
run crictl version
sudo_run crictl version
sudo_run sh -c 'crictl info | sed -n "1,200p"'
run ls -l /run/crio/crio.sock
run sh -c 'id -nG | tr " " "\n" | grep -E "crio|docker" || true'

header "4) CRI-O config (runtimes, hooks, cdi)"
run sh -c 'grep -nE "default_runtime|hooks_dir|cdi_spec_dirs" /etc/crio/crio.conf 2>/dev/null || true'
run sh -c 'grep -n "\[crio.runtime.runtimes" -n /etc/crio/crio.conf 2>/dev/null || true'
run sh -c 'sed -n "1,200p" /etc/crio/crio.conf 2>/dev/null'
run sh -c 'ls -1 /etc/crio/crio.conf.d 2>/dev/null || true'
run sh -c 'for f in /etc/crio/crio.conf.d/*.conf; do echo "--- $f"; sed -n "1,120p" "$f"; done 2>/dev/null'
run sh -c 'ls -l /usr/share/containers/oci/hooks.d 2>/dev/null || true'
run sh -c 'for f in /usr/share/containers/oci/hooks.d/*.json; do echo "--- $f"; sed -n "1,120p" "$f"; done 2>/dev/null'

header "5) containers-common"
run sh -c 'cat ~/.config/containers/registries.conf 2>/dev/null || true'
run sh -c 'cat /etc/containers/registries.conf 2>/dev/null || true'

header "6) CNI & sysctl"
run sh -c 'ls -l /etc/cni/net.d 2>/dev/null || true'
run sh -c 'for f in /etc/cni/net.d/*; do echo "--- $f"; sed -n "1,120p" "$f"; done 2>/dev/null'
run sh -c 'sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding 2>/dev/null || true'
run sh -c 'lsmod | grep br_netfilter || true'

header "7) CRI-O logs (tail $TAIL_LINES)"
sudo_run sh -c "journalctl -u crio -b --no-pager | tail -n $TAIL_LINES"

header "8) Images & storage"
sudo_run crictl images
run df -hT / /home /var/lib/containers/storage 2>/dev/null || true
sudo_run du -sh /var/lib/containers/storage 2>/dev/null || true

header "9) Docker Hub reachability"
run sh -c 'curl -Is https://registry-1.docker.io/v2/ | head -n1'

# Podman smoke removed (project focuses on CRI-O now)

if [[ "$SMOKE_CRIO" -eq 1 ]]; then
  header "11) Smoke: CRI-O runtime 'nvidia' (nvidia-smi)"
  TMPDIR="${TMPDIR:-/tmp}"
  POD_JSON="$TMPDIR/gpu-pod.json"
  CTR_JSON="$TMPDIR/gpu-ctr.json"
  cat >"$POD_JSON" <<JSON
{ "metadata":{"name":"gpu-smoke","namespace":"default","uid":"gpu-smoke-uid"},
  "log_directory":"/tmp","linux":{"cgroup_parent":"system.slice"} }
JSON
  cat >"$CTR_JSON" <<JSON
{ "metadata":{"name":"cuda-nvsmi"},
  "image":{"image":"docker.io/nvidia/cuda:12.3.2-base-ubuntu22.04"},
  "command":["nvidia-smi"], "log_path":"cuda-nvsmi.log",
  "linux":{"security_context":{"privileged":false}} }
JSON
  sudo_run crictl pull docker.io/nvidia/cuda:12.3.2-base-ubuntu22.04
  POD_ID=$(sudo_run crictl runp --runtime nvidia "$POD_JSON" | tail -n1 | awk '{print $NF}')
  echo "POD_ID=$POD_ID"
  CID=$(sudo_run crictl create "$POD_ID" "$CTR_JSON" "$POD_JSON" | tail -n1 | awk '{print $NF}')
  echo "CID=$CID"
  sudo_run crictl start "$CID"
  sleep 2
  sudo_run crictl logs "$CID" | cat
  sudo_run crictl rm -f "$CID"; sudo_run crictl rmp -f "$POD_ID"
fi

if [[ "$CHECK_SERVICES" -eq 1 ]]; then
  header "12) CRI-O pods/containers (status)"
  sudo_run crictl pods | sed -n "1,200p"
  sudo_run crictl ps -a | sed -n "1,200p"

  header "13) vLLM health (http://127.0.0.1:$VLLM_PORT)"
  run sh -c "curl -fsS http://127.0.0.1:$VLLM_PORT/health && echo ok || echo not-ready"
  run sh -c "curl -fsS http://127.0.0.1:$VLLM_PORT/v1/models | sed -n '1,80p' || true"

  header "14) Redis PING (localhost:$REDIS_PORT)"
  if have redis-cli; then
    run sh -c "redis-cli -a '$REDIS_PASSWORD' -p $REDIS_PORT PING"
  else
    echo "redis-cli not found; attempting in-container exec if available"
    RID=$(sudo_run crictl ps -a --name redis -q | tail -n1 | awk '{print $NF}')
    if [[ -n "$RID" ]]; then sudo_run crictl exec "$RID" sh -lc "redis-cli -a '$REDIS_PASSWORD' -p $REDIS_PORT PING"; fi
  fi

  header "15) Neo4j HTTP/Bolt (localhost:$NEO4J_HTTP_PORT / $NEO4J_BOLT_PORT)"
  run sh -c "curl -fsS -u '$NEO4J_USER:$NEO4J_PASSWORD' -I http://127.0.0.1:$NEO4J_HTTP_PORT/ | head -n1 || true"
  NID=$(sudo_run crictl ps -a --name neo4j -q | tail -n1 | awk '{print $NF}')
  if [[ -n "$NID" ]]; then
    run sudo_run crictl exec "$NID" sh -lc "/var/lib/neo4j/bin/cypher-shell -u '$NEO4J_USER' -p '$NEO4J_PASSWORD' 'RETURN 1'" || true
  fi

  header "16) vLLM CDI devices in spec (if container present)"
  VID=$(sudo_run crictl ps -a --name vllm -q | tail -n1 | awk '{print $NF}')
  if [[ -n "$VID" ]]; then
    run sh -c "sudo crictl inspect '$VID' | jq '.info.runtimeSpec.linux.devices // []' | sed -n '1,120p'"
  fi
fi

if [[ "$REGEN_CDI_NO_DRI" -eq 1 ]]; then
  header "(Write) Regenerate CDI excluding /dev/dri and restart CRI-O"
  sudo_run nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
  sudo_run systemctl restart crio
  header "Re-check CDI"
  run nvidia-ctk cdi list
  run sh -c 'grep -n "/dev/dri" /etc/cdi/nvidia.yaml 2>/dev/null || true'
fi

echo
echo "Done. Review sections above for mismatches (CDI vs host /dev, CRI-O runtimes, hooks)."

