# Kubernetes Demo Runbook (Kubeadm + CRI‑O + GPU Operator)

This runbook executes the installation (post‑cluster) and runs the demo on Kubernetes. It assumes you have a kubeadm cluster with CRI‑O and (optionally) the NVIDIA GPU Operator installed per `docs/INSTALL_K8S_CRIO_GPU.md`.

## Architecture (ASCII)

```
               +-----------------------------+
               |        Ingress (NGINX)      |
               |     ingress-nginx namespace |
               +---------------+-------------+
                               |
                         Host: swe.local
                               |
                     +---------v----------+
                     |  Service: demo-web |   (optional when web runs in-cluster)
                     |     swe namespace   |
                     +---------+----------+
                               |
                         +-----v-----+
                         |   Pod:    |
                         |   web     |  FastAPI demo (UI/API)
                         +-----+-----+
                               |
        +----------------------+-----------------------+
        |                      |                       |
        v                      v                       v
 +------+-------+      +-------+------+        +-------+------+
 | Service:     |      | Service:     |        | Service:     |
 | redis        |      | neo4j        |        | vllm         |  (GPU)
 +------+-------+      +-------+------+        +-------+------+
        |                      |                       |
   +----v----+            +----v----+            +-----v-----+
   |  Pod:   |            |  Pod:   |            |   Pod:    |
   |  redis  |            |  neo4j  |            |  vllm     |
   +---------+            +---------+            +-----------+
        ^                                               ^
        |                                               |
    Secret:                                         GPU Operator
  redis-auth                                        (nvidia.com/gpu)
                                                     + CDI devices

Notes:
- Namespace: `swe` for demo services; `ingress-nginx` for Ingress Controller.
- Secrets: `redis-auth`, `neo4j-auth` in `swe` namespace.
- vLLM schedules on GPU nodes (NVIDIA GPU Operator installed) and exposes `nvidia.com/gpu` resources.
- For local iteration, the web can run outside the cluster; use port-forward to Redis/Neo4j Services.
```

## Prerequisites

- Working Kubernetes cluster (kubeadm) with CRI‑O
- CNI installed (e.g., Calico)
- kubectl and helm configured to the cluster
- Optional: GPU nodes with NVIDIA GPU Operator (for vLLM)
 - Ingress Controller (NGINX). See `docs/INGRESS_INSTALL.md`.

## 1) Namespace and Secrets

```bash
kubectl create namespace swe || true

# Redis password secret
kubectl -n swe create secret generic redis-auth \
  --from-literal=password=swefleet-dev || true

# Neo4j password secret
kubectl -n swe create secret generic neo4j-auth \
  --from-literal=password=swefleet-dev || true
```

## 2) Helm install base services (Redis, Neo4j; vLLM optional)

```bash
helm dependency update deploy/helm || true
helm upgrade --install swe-fleet deploy/helm -n swe --create-namespace

kubectl get pods -n swe -o wide
kubectl get svc -n swe
```

Values reference (`deploy/helm/values.yaml`):
- `redis.host`: `redis.default.svc` (will resolve as `redis.swe.svc` by namespace)
- `neo4j.boltUri`: `bolt://neo4j.swe.svc:7687`
- `neo4j.httpUri`: `http://neo4j.swe.svc:7474`
- `vllm.enabled`: set to `true` when GPU nodes available; confirm GPU Operator status

Enable vLLM (GPU) later with:

```bash
helm upgrade swe-fleet deploy/helm -n swe \
  --set vllm.enabled=true \
  --set vllm.gpu.nvidia=true \
  --set vllm.gpu.numDevices=1
```

## 3) Port‑forward for local seeding

For local scripts to reach in‑cluster services without exposing services externally:

```bash
# In separate terminals
kubectl -n swe port-forward svc/redis 6379:6379
kubectl -n swe port-forward svc/neo4j 7474:7474
kubectl -n swe port-forward svc/neo4j 7687:7687
```

## 4) Seed demo data (CTX‑001)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .

export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=swefleet-dev
export DEMO_CASE_ID=CTX-001

python scripts/seed_context_example.py
```

Verification (optional):

```bash
# Decisions, influenced subtasks, and authors
kubectl -n swe exec -it deploy/neo4j -- \
  /var/lib/neo4j/bin/cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (c:Case {id:'CTX-001'})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)\n   OPTIONAL MATCH (d)-[:INFLUENCES]->(s:Subtask)\n   OPTIONAL MATCH (d)-[:AUTHORED_BY]->(a:Actor)\n   RETURN d.id, collect(DISTINCT s.id), collect(DISTINCT a.id) ORDER BY d.id;"
```

## 5) Run the demo frontend locally

```bash
pip install -e .[web]
HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

Open:
- UI: `http://localhost:8080/ui/report?case_id=CTX-001`
- API: `http://localhost:8080/api/report?case_id=CTX-001&persist=false`

## 5.1) Optional: Access the demo via Ingress locally (no external exposure)

If you deployed the simple demo frontend Deployment/Service and the Ingress manifest in `deploy/k8s/`, you can test through the NGINX Ingress Controller without exposing it externally.

1) Add hostnames to `/etc/hosts` (on your workstation):

```bash
sudo sh -c 'printf "\n127.0.0.1 swe-ai-fleet.local\n127.0.0.1 demo.swe-ia-fleet.local\n" >> /etc/hosts'
```

2) Start a port-forward to the Ingress Controller:

```bash
# Use privileged port 80 with sudo and explicit kubeconfig
sudo KUBECONFIG=/home/ia/.kube/config \
  kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 80:80

# Or preserve env
export KUBECONFIG=/home/ia/.kube/config
sudo -E kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 80:80
```

3) Verify routing with curl (Host headers):

```bash
curl -s -H 'Host: swe-ai-fleet.local' http://127.0.0.1/
curl -s -H 'Host: demo.swe-ia-fleet.local' http://127.0.0.1/
```

Expected for the echo sample:

```
hello swe-ai-fleet from kubernetes!!
```

Alternative without sudo (use high local port):

```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80 --address 127.0.0.1
curl -s -H 'Host: swe-ai-fleet.local' http://127.0.0.1:8080/
```

Troubleshooting quick checks:

- Ensure Ingress exists in `swe` and points to `Service demo-frontend:8080`.
- `kubectl -n ingress-nginx get pods,svc` show controller Running and Service Ports 80/443.
- If curl returns 404, check `ingressClassName: nginx` and hostname matches `/etc/hosts`.

## 6) Optional: Deploy vLLM and test health

Enable vLLM via Helm (see step 2), then:

```bash
kubectl -n swe port-forward svc/vllm 8000:8000
curl -fsS http://127.0.0.1:8000/health && echo ok
curl -sS http://127.0.0.1:8000/v1/models | jq .
```

Point the demo to vLLM:

```bash
export LLM_BACKEND=vllm
export VLLM_ENDPOINT=http://127.0.0.1:8000/v1
export VLLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

## 7) Troubleshooting

- Secrets mismatch → Neo4j/Redis auth failures: recreate secrets and restart pods.
- Port‑forward conflicts → free the ports or use alternate local ports.
- vLLM not scheduling → confirm GPU Operator pods Running and node allocatable `nvidia.com/gpu`.
- DNS in scripts: favor port‑forward with localhost rather than direct Service DNS from host.

## 8) Cleanup

```bash
helm uninstall swe-fleet -n swe || true
kubectl delete ns swe || true
```

## Notes

- This runbook keeps the frontend local to simplify iteration; a future chart will package the web service for in‑cluster deployment.
- For production‑like exposure, use Ingress/Gateway and configure secrets via sealed secrets or external secret managers.
