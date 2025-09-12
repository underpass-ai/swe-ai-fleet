# Installation Guide

This guide explains how to install and run SWE AI Fleet on a single Linux workstation using CRI-O, plus optional steps for Ray and Kubernetes.

## Prerequisites

- Linux with systemd
- Python 3.13+
- CRI-O runtime
- Optional: Helm, kubectl, kind for K8s workflows
 - Recommended hardware: 4× NVIDIA GPUs (≥24 GB VRAM) for local LLM inference

## 1) Clone the repository

```bash
git clone https://github.com/underpass-ai/swe-ai-fleet.git
cd swe-ai-fleet
```

## 2) Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Run tests to validate setup:

```bash
python -m pytest tests/unit -v
```

## 3) Container runtime (CRI-O)

Install packages (Arch Linux example):

```bash
sudo pacman -S --noconfirm cri-o crun conmon containers-common skopeo buildah
sudo systemctl enable --now crio
```

Configure short-name resolution (rootless):

```bash
mkdir -p ~/.config/containers
cat > ~/.config/containers/registries.conf << 'EOF'
unqualified-search-registries = ["docker.io", "quay.io"]
EOF
```

Note: Use host networking in CRI-O manifests for localhost services.

## 4) Start local services (Redis + RedisInsight + Neo4j)

Use CRI-O manifests under `deploy/crio` for host-networked services.

Redis stack:

```bash
export REDIS_PASSWORD=swefleet-dev
sudo crictl runp deploy/crio/redis-pod.json
POD=$(sudo crictl pods -q --name redis | head -n1)
sudo crictl create "$POD" deploy/crio/redis-ctr.json deploy/crio/redis-pod.json
sudo crictl start $(sudo crictl ps -a -q --name redis | head -n1)
```

Neo4j:

```bash
export NEO4J_AUTH=neo4j/swefleet-dev
sudo crictl runp deploy/crio/neo4j-pod.json
POD=$(sudo crictl pods -q --name neo4j | head -n1)
sudo crictl create "$POD" deploy/crio/neo4j-ctr.json deploy/crio/neo4j-pod.json
sudo crictl start $(sudo crictl ps -a -q --name neo4j | head -n1)
```

Service endpoints (host network):

- Redis: `localhost:6379` (password: `${REDIS_PASSWORD}`)
- RedisInsight: `http://localhost:5540`
- Neo4j Browser: `http://localhost:7474` (auth: `neo4j/<password>`)
- Neo4j Bolt: `bolt://localhost:7687`

If you prefer bridged networking, ensure `/dev/net/tun` is available and use `slirp4netns` or `pasta` without `network_mode: host`.

### Verify services

```bash
# Redis ping (requires password)
redis-cli -a "$REDIS_PASSWORD" -h 127.0.0.1 PING

# Neo4j health
sudo crictl exec $(sudo crictl ps -a -q --name neo4j | head -n1) /var/lib/neo4j/bin/cypher-shell -u neo4j -p "${NEO4J_AUTH##*/}" "RETURN 1;"
```

## 5) Project smoke tests

With Redis and Neo4j running:

```bash
python -m pytest tests/integration -v
python -m pytest tests/e2e -v
```

## 6) Seed example data (Context bounded context)

Populate Redis and Neo4j with a tiny demo case/plan/decisions:

```bash
# Ensure services are up (see step 4)
export REDIS_URL="redis://:swefleet-dev@localhost:6379/0"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="swefleet-dev"
export DEMO_CASE_ID="CTX-001"

python scripts/seed_context_example.py
```

After seeding:

- Redis keys (examples):
  - `swe:case:CTX-001:spec`
  - `swe:case:CTX-001:planning:draft`
  - `swe:case:CTX-001:planning:stream`
- Neo4j graph:
  - `(:Case {id:"CTX-001"})-[:HAS_PLAN]->(:PlanVersion {id:"P-CTX-001"})`
  - `(:PlanVersion)-[:CONTAINS_DECISION]->(:Decision {id:"D1"|"D2"})`
  - `(:Decision)-[:INFLUENCES]->(:Subtask {id:"S1"|"S2"})`
  - `(:Decision)-[:AUTHORED_BY]->(:Actor {id:"actor:planner"})`

### Query the demo graph

```bash
sudo crictl exec $(sudo crictl ps -a -q --name neo4j | head -n1) /var/lib/neo4j/bin/cypher-shell -u neo4j -p "${NEO4J_AUTH##*/}" \
sudo crictl exec $(sudo crictl ps -a -q --name neo4j | head -n1) /var/lib/neo4j/bin/cypher-shell -u neo4j -p "${NEO4J_AUTH##*/}" \
  "MATCH (c:Case {id:'CTX-001'})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)
   OPTIONAL MATCH (d)-[:INFLUENCES]->(s:Subtask)
   OPTIONAL MATCH (d)-[:AUTHORED_BY]->(a:Actor)
   RETURN d.id, collect(DISTINCT s.id), collect(DISTINCT a.id)
   ORDER BY d.id;"
```

## 6) Optional: Ray (local, no Kubernetes)

```bash
pip install "ray[default]"
ray start --head --dashboard-host=0.0.0.0
ray status
# Submit a quick job
ray job submit --address http://127.0.0.1:8265 -- python -c "print('hello from ray')"
```

## 7) Optional: Kubernetes (kind + Helm)

```bash
kind create cluster --name swe-fleet
kubectl get nodes
# Install KubeRay and required charts using deploy/helm as reference
```

## Troubleshooting

- Use CRI-O host networking in manifests.
- Ensure passwords and env variables are consistent across clients.
- Redis auth: connect with URL `redis://:<pass>@localhost:6379/0`.
- vLLM multi‑GPU: adjust `--tensor-parallel-size` and `--gpu-memory-utilization`.

## Uninstall / teardown

```bash
for f in /tmp/{redis,ri,vllm,neo4j}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{redis,ri,vllm,neo4j}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```


