> Status: Advanced/Experimental — Standalone CRI‑O path
>
> This standalone CRI‑O runbook is intended for power users and local diagnostics. For most users and production‑like setups, prefer Kubernetes + CRI‑O with the NVIDIA GPU Operator. See: [INSTALL_K8S_CRIO_GPU.md](INSTALL_K8S_CRIO_GPU.md)

## EdgeCrew local setup on Arch Linux with CRI-O (GPU)

This guide covers a local, single-node setup using CRI-O + NVIDIA CDI, vLLM, Redis, Neo4j, and RedisInsight for the demo.

### Prerequisites
- Arch Linux with NVIDIA drivers (verify `nvidia-smi`)
- CRI-O installed and running (`systemctl status crio`)
- NVIDIA Container Toolkit (`nvidia-ctk`) with CDI integration
- Python 3.11+ virtualenv for the project

### 1) NVIDIA CDI for CRI-O
Regenerate CDI (exclude /dev/dri), then restart CRI-O:
```bash
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
sudo systemctl restart crio
sudo nvidia-ctk cdi list
```

### 2) Project venv and deps
```bash
cd /home/ia/develop/swe-ai-fleet
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 3) Start Redis and RedisInsight (CRI-O)
Use host networking; password: `swefleet-dev`.
```bash
sudo crictl runp deploy/crio/redis-pod.json | tee /tmp/redis.pod
POD=$(cat /tmp/redis.pod)
sudo crictl create "$POD" deploy/crio/redis-ctr.json deploy/crio/redis-pod.json | tee /tmp/redis.ctr
sudo crictl start $(cat /tmp/redis.ctr)

sudo crictl runp deploy/crio/redisinsight-pod.json | tee /tmp/ri.pod
POD=$(cat /tmp/ri.pod)
sudo crictl create "$POD" deploy/crio/redisinsight-ctr.json deploy/crio/redisinsight-pod.json | tee /tmp/ri.ctr
sudo crictl start $(cat /tmp/ri.ctr)
# UI: http://127.0.0.1:5540
```

### 4) Start vLLM (GPU, CRI-O)
```bash
sudo crictl runp --runtime nvidia deploy/crio/vllm-pod.json | tee /tmp/vllm.pod
POD=$(cat /tmp/vllm.pod)
sudo crictl create "$POD" deploy/crio/vllm-ctr.json deploy/crio/vllm-pod.json | tee /tmp/vllm.ctr
sudo crictl start $(cat /tmp/vllm.ctr)
curl -fsS http://127.0.0.1:8000/health && echo ok
```

### 5) Start Neo4j (CRI-O) and set password
```bash
sudo crictl pull docker.io/neo4j:5
sudo crictl runp deploy/crio/neo4j-pod.json | tee /tmp/neo4j.pod
POD=$(cat /tmp/neo4j.pod)
sudo crictl create "$POD" deploy/crio/neo4j-ctr.json deploy/crio/neo4j-pod.json | tee /tmp/neo4j.ctr
sudo crictl start $(cat /tmp/neo4j.ctr)
curl -fsS http://127.0.0.1:7474/ && echo http-ok
```
If first run requires password change, use:
```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec "$CID" /var/lib/neo4j/bin/cypher-shell -d system -u neo4j -p neo4j "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'swefleet-dev'"
```

### 6) Seed demo data
```bash
source .venv/bin/activate
export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev
python scripts/seed_context_example.py
```

### 7) Log LLM conversations (real)
```bash
source .venv/bin/activate
export LLM_BACKEND=vllm VLLM_ENDPOINT=http://127.0.0.1:8000/v1 VLLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
python scripts/log_conversation.py --case-id CTX-001 --session-id sess-ctx-001-1 --role agent:dev-1 --task-id S1
```

### 8) Generate report
The Decision Enriched Report includes graph decisions and recent LLM conversations.
```bash
python - <<'PY'
from swe_ai_fleet.reports.decision_enriched_report import DecisionEnrichedReportUseCase
from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter as R
from swe_ai_fleet.context.adapters.neo4j_query_store import Neo4jQueryStore, Neo4jConfig
from swe_ai_fleet.reports.adapters.neo4j_decision_graph_read_adapter import Neo4jDecisionGraphReadAdapter
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.memory.redis_store import RedisStoreImpl
case='CTX-001'
rep=DecisionEnrichedReportUseCase(R(RedisStoreImpl("redis://:swefleet-dev@localhost:6379/0").client),
  Neo4jDecisionGraphReadAdapter(Neo4jQueryStore(Neo4jConfig(uri="bolt://localhost:7687",user="neo4j",password="swefleet-dev"))))\
  .generate(ReportRequest(case_id=case, include_constraints=False))
open("demo/CTX-001-report.md","w").write(rep.markdown)
print("written: demo/CTX-001-report.md")
PY
```

### 9) Stop/Clean
```bash
for f in /tmp/{redis,ri,vllm,neo4j}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{redis,ri,vllm,neo4j}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```

### Diagnostics & Troubleshooting
- Run the diagnostic script to check GPU/CDI/CRI-O and services:
```bash
bash scripts/check_crio_nvidia_env.sh --check-services
```
- See `docs/CRIO_DIAGNOSTICS.md` (what each check validates and fixes) and `docs/TROUBLESHOOTING_CRIO.md` for common errors.


