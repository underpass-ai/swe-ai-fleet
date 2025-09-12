## CRI-O Demo Runbook (Web, Kong, vLLM GPU)

Prereqs: CRI-O running, `crictl` configured; NVIDIA CDI for GPU (see docs/INSTALL_CRIO.md).

### 1) Start core services (Redis, Neo4j, vLLM)

Follow `deploy/crio/README.md` for Redis/Neo4j/vLLM. Ensure:

- Redis: password `swefleet-dev`; port 6379
- Neo4j: `neo4j/swefleet-dev`; Bolt 7687; HTTP 7474
- vLLM: health OK; endpoint exported as `VLLM_ENDPOINT=https://127.0.0.1:8000/v1` if using TLS proxy, else use your HTTPS endpoint

### 2) Seed demo data

```bash
source .venv/bin/activate
export REDIS_URL=redis://:swefleet-dev@127.0.0.1:6379/0
export NEO4J_URI=bolt://127.0.0.1:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev
python scripts/seed_context_example.py
```

### 3) Start Web server (CRI-O)

```bash
sudo crictl runp deploy/crio/web-pod.json | tee /tmp/web.pod
WP=$(cat /tmp/web.pod)
sudo crictl create "$WP" deploy/crio/web-ctr.json deploy/crio/web-pod.json | tee /tmp/web.ctr
sudo crictl start $(cat /tmp/web.ctr)
# UI: http://127.0.0.1:8080/
```

### 4) Start Kong API Gateway (CRI-O)

```bash
sudo crictl runp deploy/crio/kong-pod.json | tee /tmp/kong.pod
KP=$(cat /tmp/kong.pod)
sudo crictl create "$KP" deploy/crio/kong-ctr.json deploy/crio/kong-pod.json | tee /tmp/kong.ctr
sudo crictl start $(cat /tmp/kong.ctr)
# Proxy: http://127.0.0.1:8081
```

Routes in `deploy/podman/kong/kong.yml` forward to web, vLLM, RedisInsight, Neo4j, and Ray.

### 5) Validate

- Web UI: `http://127.0.0.1:8080/ui/report?case_id=CTX-001`
- API (via Kong): `http://127.0.0.1:8081/swe-web/api/report?case_id=CTX-001&persist=false`
- vLLM models (via Kong): `http://127.0.0.1:8081/v1/models`

### 6) Cleanup

```bash
for f in /tmp/{web,kong}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{web,kong}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```


