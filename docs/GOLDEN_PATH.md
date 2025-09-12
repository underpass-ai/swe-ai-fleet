## Golden Path — 10 minutes to first value

Goal: Render the Decision‑Enriched report for `CTX-001` using local CRI‑O services and a local FastAPI frontend.

### 1) Start services with CRI‑O (Redis, Neo4j; optional RedisInsight and vLLM)

Use these basic commands (host networking). For details, see `deploy/crio/README.md`.

```bash
# Redis (password: swefleet-dev)
sudo crictl runp deploy/crio/redis-pod.json | tee /tmp/redis.pod
POD=$(cat /tmp/redis.pod)
sudo crictl create "$POD" deploy/crio/redis-ctr.json deploy/crio/redis-pod.json | tee /tmp/redis.ctr
sudo crictl start $(cat /tmp/redis.ctr)

# Neo4j (user: neo4j / pass: swefleet-dev)
sudo crictl runp deploy/crio/neo4j-pod.json | tee /tmp/neo4j.pod
POD=$(cat /tmp/neo4j.pod)
sudo crictl create "$POD" deploy/crio/neo4j-ctr.json deploy/crio/neo4j-pod.json | tee /tmp/neo4j.ctr
sudo crictl start $(cat /tmp/neo4j.ctr)

# (Optional) RedisInsight UI: http://127.0.0.1:5540
sudo crictl runp deploy/crio/redisinsight-pod.json | tee /tmp/ri.pod
POD=$(cat /tmp/ri.pod)
sudo crictl create "$POD" deploy/crio/redisinsight-ctr.json deploy/crio/redisinsight-pod.json | tee /tmp/ri.ctr
sudo crictl start $(cat /tmp/ri.ctr)

# (Optional) vLLM GPU (requires NVIDIA CDI)
sudo crictl runp --runtime nvidia deploy/crio/vllm-pod.json | tee /tmp/vllm.pod
POD=$(cat /tmp/vllm.pod)
sudo crictl create "$POD" deploy/crio/vllm-ctr.json deploy/crio/vllm-pod.json | tee /tmp/vllm.ctr
sudo crictl start $(cat /tmp/vllm.ctr)
# vLLM health: curl -fsS http://127.0.0.1:8000/health && echo ok
```

Default ports: Redis 6379, RedisInsight 5540, Neo4j HTTP 7474 / Bolt 7687, vLLM 8000.

### 2) Seed demo data (CTX‑001)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev
python scripts/seed_context_example.py
```

### 3) Start the frontend (local)

```bash
pip install -e .[web]
HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

### 4) Verify the demo

- UI: `http://localhost:8080/ui/report?case_id=CTX-001`
- API: `http://localhost:8080/api/report?case_id=CTX-001&persist=false`

Sample API response (truncated):

```json
{
  "case_id": "CTX-001",
  "plan_id": "P-CTX-001",
  "generated_at_ms": 1730000000000,
  "markdown": "# Decision-Enriched Report...",
  "stats": {"events": 1, "decisions": 2, "subtasks": 2}
}
```

Optional LLM:

- Health: `http://localhost:8080/healthz/llm`
- Seed LLM conversations: `http://localhost:8080/api/demo/seed_llm?case_id=CTX-001`

### 5) Quick cleanup

```bash
for f in /tmp/{redis,ri,vllm,neo4j}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{redis,ri,vllm,neo4j}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```

### Common issues

- "Case spec not found": run the seed in step 2 and confirm `REDIS_URL`.
- Neo4j Unauthorized: expected password `swefleet-dev` (env `NEO4J_PASSWORD`).
- Redis Connection refused: ensure Redis listens on `127.0.0.1:6379` and password is set.
- vLLM unavailable: it’s optional; if no GPU/CDI, skip the service.


