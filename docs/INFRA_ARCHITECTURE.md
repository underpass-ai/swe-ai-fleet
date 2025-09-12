# Infrastructure Architecture (CRI‑O now; Kubernetes next)

## Goal

Describe how to deploy and operate the demo with CRI‑O (current phase) and how it will evolve to Kubernetes (next phase) while keeping the same logical components.

## Logical Components

- **Data services**: Redis (short-term memory), Neo4j (decision graph)
- **LLM runtime**: vLLM (OpenAI API)
- **UI/API**: FastAPI frontend (reports and demo utilities)
- **Observability**: logs (journald/CRI‑O), metrics (future)
- **Security**: secrets (Redis/Neo4j passwords), container isolation

---

## Infrastructure with CRI‑O (current phase)

### Topology (host networking)

```
┌────────────┐     ┌────────────┐     ┌─────────┐
│  Frontend  │───▶ │   Redis    │     │ Redis   │
│  FastAPI   │     │  (6379)    │◀──▶ │Insight  │
│  (8080)    │     └────────────┘     │ (5540)  │
│           ┌┴┐                        └─────────┘
│           │ │                        ┌─────────┐
│           │ │──────▶ Neo4j (7474/7687)         │
│           │ │                        │  vLLM   │
│           └─┘──────▶ vLLM API (8000) │  (8000) │
└────────────┘                        └─────────┘
```

- Networking: `namespace_options.network=2` (hostNetwork) in CRI‑O Pods
- GPU: NVIDIA CDI with `nvidia` runtime handler for vLLM
- Secrets: environment variables or mounted files (e.g., Redis/Neo4j passwords)

### Manifests and scripts

- `deploy/crio/*.json`: Pods and Containers for Redis, RedisInsight, Neo4j, vLLM
- `scripts/vllm_crio.sh`: start/stop vLLM with GPU (runtime `nvidia`)

### Startup flow (summary)

1) Redis + RedisInsight
- `sudo crictl runp deploy/crio/redis-pod.json`
- `sudo crictl create <POD> deploy/crio/redis-ctr.json deploy/crio/redis-pod.json && sudo crictl start <CID>`
- (Optional) RedisInsight with its manifests

2) Neo4j
- Pod/Container with `deploy/crio/neo4j-*.json`
- Set password if first time

3) vLLM (GPU)
- `sudo bash scripts/vllm_crio.sh start` (includes CDI and `nvidia` handler)
- Health: `curl -s http://127.0.0.1:8000/v1/models`

4) Frontend
- Local (recommended): `pip install -e .[web] && swe_ai_fleet-web`

### Security and operations

- Isolation: non-privileged containers, resource limits in manifests
- Secrets: not stored in repo; load via env/external files
- Logs: `journalctl -u crio` + `crictl logs <cid>`
- Diagnostics: `scripts/check_crio_nvidia_env.sh --check-services`

---

## Infrastructure with Kubernetes (next phase)

### Topology (Services and Helm Chart)

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
│ Ingress   │──▶│  Frontend │──▶ │  Redis   │    │  Neo4j   │
│/Gateway   │    │  (Svc)   │    │  (Svc)   │    │  (Svc)   │
└──────────┘    └───────────┘    └──────────┘    └──────────┘
                      │                  │              │
                      └──────────────────┴──────────────┘
                                     │
                                 ┌────▼────┐
                                 │  vLLM   │ (Svc, GPU)
                                 └─────────┘
```

- Dedicated namespaces (e.g., `swe`)
- Secrets for passwords (`redis-auth`, `neo4j-auth`)
- NVIDIA Device Plugin for GPU (vLLM)
- Helm charts in `deploy/helm/`

### Helm values (summary)

- `deploy/helm/values.yaml`:
  - Redis: `redis.host`, `redis.passwordSecretName`
  - Neo4j: `neo4j.boltUri`/`httpUri`, auth secrets
  - vLLM: `vllm.enabled=false` (enable when GPU available), `vllm.endpoint`, `vllm.model`, `vllm.gpu.*`

### Deployment flow (draft)

1) Prereqs: `kubectl`, `helm`, cluster and (optional) NVIDIA Device Plugin
2) Secrets: `kubectl create secret generic redis-auth ...` and `neo4j-auth ...`
3) Install: `helm install swe-fleet deploy/helm -n swe --create-namespace`
4) Validate pods and services; configure Ingress/Gateway if applicable

### Security and operations

- Policies: NetworkPolicy, RBAC, PodSecurity
- Observability: metrics and logs (to be defined in K8s phase)
- Scale: Ray/KubeRay in dedicated namespace (future)

---

## Evolution and functional parity

- The demo logic (Redis, Neo4j, vLLM, Frontend) remains the same across CRI‑O and K8s
- Frontend endpoints do not change; only service resolution (localhost vs Services DNS)
- Security and resource control improve when moving to K8s (native policies)

## References

- CRI‑O: `deploy/crio/README.md`, `docs/INSTALL_CRIO.md`, `docs/CRIO_DIAGNOSTICS.md`
- Kubernetes: `deploy/helm/`, `docs/DEPLOYMENT.md` (Kubernetes section)
