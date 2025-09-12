# Deployment Guide

EdgeCrew supports three common scenarios. Choose the one that matches your environment and scale.

## Workstation

- Single machine baseline: 2×24 GB GPUs (dev/test). Recommended: 4–8×24 GB for production‑like throughput
- CRI-O runtime
- Python 3.13 virtual environment

Steps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e .
python -m pytest tests/unit -v
```

## Homelab / Edge

- Single-node setup; container runtime required
- Optionally run Kubernetes (kind/k3s) to simulate cluster workflows

Suggested flow:

1. Prepare the Python environment (as above)
2. Validate with unit/integration tests
3. Use the E2E CLI to dry-run flows:

```bash
swe_ai_fleet-e2e --help
```

### Demo Frontend (local)

Minimal FastAPI UI to visualize the report for a given `case_id`.

Steps:

```bash
pip install -e .[web]
HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

Variables:

```bash
export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=swefleet-dev
```

Useful URLs:

- Home: `http://localhost:8080/`
- UI: `http://localhost:8080/ui/report?case_id=CASE-123`
- API: `http://localhost:8080/api/report?case_id=CASE-123&persist=false`

## Ray (native, no Kubernetes)

Run EdgeCrew on local Ray or a lightweight cluster without Kubernetes.

Prerequisites:

- `pip install "ray[default]"`
- Puertos abiertos para dashboard (8265) si usas acceso remoto

Local head:

```bash
ray start --head --dashboard-host=0.0.0.0
ray status

# Job simple
ray job submit --address http://127.0.0.1:8265 -- python -c "print('hello from ray')"
```

Remote worker (optional):

```bash
ray start --address='ray://<HEAD_IP>:10001'  # or --address='<HEAD_IP>:6379' depending on setup
```

## Enterprise Cluster

- Kubernetes (next phase) + Ray/KubeRay for horizontal scaling (multi‑node, each node ≥1×24 GB)
- Integration with identity, artifacts, and enterprise observability

High-level steps (draft):

1. Provision a Kubernetes cluster with GPU workers (as needed)
2. Install base services via Helm
3. Configure namespaces, storage classes, network policies
4. Deploy EdgeCrew workloads with `deploy/helm` and connect to CI/CD

### Helm values (reference)

Adjust `deploy/helm/values.yaml` before installing:

- Redis:
  - `redis.host`: Redis service DNS (e.g., `redis.default.svc`)
  - `redis.port`: 6379
  - `redis.passwordSecretName` and `redis.passwordSecretKey`: secret with the password

- Neo4j:
  - `neo4j.boltUri`: `bolt://neo4j.default.svc:7687`
  - `neo4j.httpUri`: `http://neo4j.default.svc:7474`
  - `neo4j.auth.username`: `neo4j`
  - `neo4j.auth.passwordSecretName` / `passwordSecretKey`: password secret

- vLLM (optional, GPU):
  - `vllm.enabled`: `false` by default (enable when GPU is available)
  - `vllm.endpoint`: `http://vllm.default.svc:8000/v1`
  - `vllm.model`: model name loaded in vLLM
  - `vllm.gpu.nvidia`: `true` to use the NVIDIA Device Plugin
  - `vllm.gpu.numDevices`: number of GPUs per pod

Notes:
- Create required secrets (`redis-auth`, `neo4j-auth`) with `kubectl create secret ...` and names/keys matching `values.yaml`.
- For GPU, install and validate the NVIDIA Device Plugin in the cluster.

Notes:

- Keep secrets externalized and injected at runtime (e.g., sealed secrets)
- Enforce resource quotas and PodSecurity standards
- Prefer rootless runtimes and minimal base images

## Health checks and validation

- Unit tests: `python -m pytest tests/unit -v`
- Integration tests: `python -m pytest tests/integration -v`
- End-to-end (dry-run): `swe_ai_fleet-e2e --help`

## Why CRI-O (for this project)

EdgeCrew prefers CRI-O for its alignment with Kubernetes, security, and CDI support for GPUs:

- Security and isolation:
  - CRI-O closely follows the Kubernetes container stack (OCI runtime + runc/crun), with smaller surface and no single privileged daemon.
  - Natural integration with Pod/RuntimeClass policies and SELinux/AppArmor.
- GPU compatibility (NVIDIA CDI):
  - Direct integration with NVIDIA Container Toolkit via CDI (declarative device injection), the same mechanism used in Kubernetes.
  - Less reliance on ad‑hoc flags; the `nvidia` runtime is selected by handler.
- Parity with clusters:
  - What you validate locally (CRI-O + CDI + hostNetwork) is very similar to how it will work in K8s with RuntimeClass and KubeRay.
- Observability and traceability:
  - Familiar tools (`crictl`, `journalctl`) for low-level debugging.
- Performance and footprint:
  - Lower daemon overhead and alignment with Kubernetes practices.


