## Podman and CRI-O — how they relate and how to use both

EdgeCrew embraces both Podman and CRI-O because they share the same OCI building blocks (conmon, runc/crun, containers/storage) and map cleanly to local development and cluster‑like execution.

### Relationship in a nutshell
- Podman: developer‑friendly CLI for running/building containers (rootless or rootful). No long‑running daemon.
- CRI-O: Kubernetes Container Runtime Interface (CRI) implementation used by Kubelet. Controlled via `crictl`.
- Shared components: OCI runtime (runc/crun), `conmon`, image/storage backends (often `/var/lib/containers/storage`). This allows similar behavior and, in many distros, shared image store.

When to use which:
- Use Podman to iterate fast (build, run, test) and to smoke‑test GPU containers with CDI.
- Use CRI-O to emulate how workloads run under Kubernetes (pod/ctr JSONs, host networking, runtime handler `nvidia`).

### GPU (NVIDIA) with Podman via CDI
Prereqs: NVIDIA Container Toolkit + CDI spec present (`/etc/cdi/nvidia.yaml`).

Smoke test:
```bash
podman run --rm --device nvidia.com/gpu=all \
  docker.io/nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi
```

vLLM (example, 2 GPUs) using host network:
```bash
podman run -d --name vllm --network host --device nvidia.com/gpu=all \
  docker.io/vllm/vllm-openai:latest \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --dtype auto \
  --host 0.0.0.0 --port 8000

curl -fsS http://127.0.0.1:8000/health && echo ok
podman logs -f vllm | sed -n '1,120p'
```

### Redis and Neo4j with Podman (host network)
Redis (password `swefleet-dev`):
```bash
podman run -d --name redis --network host docker.io/redis:7-alpine \
  redis-server --appendonly no --save '' \
  --requirepass swefleet-dev --bind 0.0.0.0 --protected-mode no
redis-cli -a swefleet-dev PING
```

Neo4j:
```bash
podman run -d --name neo4j --network host docker.io/neo4j:5 \
  -e NEO4J_AUTH=neo4j/swefleet-dev \
  -e NEO4J_server_default__listen__address=0.0.0.0 \
  -e NEO4J_server_http__listen__address=0.0.0.0:7474 \
  -e NEO4J_server_bolt__listen__address=0.0.0.0:7687
curl -fsS http://127.0.0.1:7474/ | head -n1 || true
```

### Moving from Podman to CRI-O runs
Podman is great for quick loops. To emulate Kubernetes more closely:
- Use CRI-O manifests (JSON) and `crictl` (see `deploy/crio/*.json` and `docs/INSTALL_CRIO.md`).
- Select `--runtime nvidia` for GPU pods and confirm CDI injection with `crictl inspect <cid> | jq '.info.runtimeSpec.linux.devices'`.
- Prefer host networking for localhost endpoints during the demo (as with Podman `--network host`).

### Storage and images
On most setups, both Podman and CRI-O use `/var/lib/containers/storage`. Images you pull/build with Podman can be directly consumed by CRI-O. If they diverge in your distro, use `crictl pull` or `skopeo copy` to mirror images.

### Diagnostics
Use the combined diagnostic script:
```bash
bash scripts/check_crio_nvidia_env.sh --smoke-podman --check-services
```
It verifies CDI, CRI-O, vLLM, Redis, and Neo4j endpoints, and can smoke‑test Podman/CRI‑O GPU containers.


