## CRI-O Demo Runbook (Web, Kong, vLLM GPU)

Prereqs: CRI-O running, `crictl` configured; NVIDIA CDI for GPU (see docs/INSTALL_CRIO.md).

### 1) Environment

Copy `.env.example` to `.env` and adjust if needed (passwords, GPUs).

### 2) Start core services (Redis, Neo4j, vLLM)

You can use helper scripts (they load `.env`):

```bash
sudo bash scripts/redis_crio.sh start
sudo bash scripts/neo4j_crio.sh start
sudo bash scripts/vllm_crio.sh start
```

Or follow `deploy/crio/README.md` raw steps. Ensure:

- Redis: password `swefleet-dev`; port 6379
- Neo4j: `neo4j/swefleet-dev` (>=8 chars); Bolt 7687; HTTP 7474
- vLLM: health OK; endpoint exported as `VLLM_ENDPOINT=https://127.0.0.1:8000/v1` if using TLS proxy, else use your HTTPS endpoint

### 3) Seed demo data

```bash
source .venv/bin/activate
export REDIS_URL=redis://:swefleet-dev@127.0.0.1:6379/0
export NEO4J_URI=bolt://127.0.0.1:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev
python scripts/seed_context_example.py
```

### 4) Start Web server (CRI-O)

```bash
sudo crictl runp deploy/crio/web-pod.json | tee /tmp/web.pod
WP=$(cat /tmp/web.pod)
sudo crictl create "$WP" deploy/crio/web-ctr.json deploy/crio/web-pod.json | tee /tmp/web.ctr
sudo crictl start $(cat /tmp/web.ctr)
# UI: http://127.0.0.1:8080/
```

### 5) Start Kong API Gateway (CRI-O)

```bash
sudo crictl runp deploy/crio/kong-pod.json | tee /tmp/kong.pod
KP=$(cat /tmp/kong.pod)
sudo crictl create "$KP" deploy/crio/kong-ctr.json deploy/crio/kong-pod.json | tee /tmp/kong.ctr
sudo crictl start $(cat /tmp/kong.ctr)
# Proxy: http://127.0.0.1:8081
```

Routes in `deploy/podman/kong/kong.yml` forward to web, vLLM, RedisInsight, Neo4j, and Ray.

### 6) Validate

- Web UI: `http://127.0.0.1:8080/ui/report?case_id=CTX-001`
- API (via Kong): `http://127.0.0.1:8081/api/report?case_id=CTX-001&persist=false`
- vLLM models (via Kong): `http://127.0.0.1:8081/v1/models`

### Quick Fix: Neo4j auth reset

If seeding fails with Neo4j Unauthorized, reset the initial password (>=8 chars) and restart inside the container:

```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j stop || true
sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j-admin dbms set-initial-password swefleet-dev
sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j start &
sleep 8
sudo crictl exec -i "$CID" /var/lib/neo4j/bin/cypher-shell -a bolt://127.0.0.1:7687 -u neo4j -p swefleet-dev "RETURN 1 AS n"
```

Re-run the seed step afterwards.

### 7) Cleanup

```bash
for f in /tmp/{web,kong}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{web,kong}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```


