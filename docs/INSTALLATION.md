# Installation Guide

This guide explains how to install and run SWE AI Fleet on a single Linux workstation using Podman/CRI-O, plus optional steps for Ray and Kubernetes.

## Prerequisites

- Linux with systemd
- Python 3.13+
- Podman 5.x and CRI-O (preferred) or Docker-compatible runtime
- Optional: Helm, kubectl, kind for K8s workflows

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

## 3) Container runtime (Podman/CRI-O)

Install packages (Arch Linux example):

```bash
sudo pacman -S --noconfirm podman podman-compose crun slirp4netns fuse-overlayfs skopeo buildah conmon containers-common cri-o
sudo systemctl enable --now crio
```

Configure short-name resolution (rootless):

```bash
mkdir -p ~/.config/containers
cat > ~/.config/containers/registries.conf << 'EOF'
unqualified-search-registries = ["docker.io", "quay.io"]
EOF
```

Note: On systems without `/dev/net/tun`, host networking is recommended for rootless containers.

## 4) Start local services (Redis + RedisInsight + Neo4j)

We ship compose files under `deploy/docker`. Images are fully-qualified and configured for host networking when running rootless.

Redis stack:

```bash
export REDIS_PASSWORD=redispass
podman-compose -f deploy/docker/redis/docker-compose.yml up -d
podman logs --tail=50 swe-ai-fleet-redis
```

Neo4j:

```bash
export NEO4J_AUTH=neo4j/sweai1234  # minimum 8-char password required by Neo4j
podman-compose -f deploy/docker/neo4j/docker-compose.yml up -d
podman logs --tail=80 swe-ai-fleet-neo4j
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
podman exec swe-ai-fleet-neo4j cypher-shell -u neo4j -p "${NEO4J_AUTH##*/}" "RETURN 1;"
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
export REDIS_URL="redis://:redispass@localhost:6379/0"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="sweai1234"
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
podman exec swe-ai-fleet-neo4j cypher-shell -u neo4j -p "${NEO4J_AUTH##*/}" \
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

- Missing `/dev/net/tun` when rootless: switch to `network_mode: host` (as in our compose files) or run rootful.
- Image short-name errors: ensure `~/.config/containers/registries.conf` contains `unqualified-search-registries`.
- Neo4j rejects password: set `NEO4J_AUTH=neo4j/<min8chars>`.
- Redis protected-mode and auth: ensure `REDIS_PASSWORD` is set; connect with URL `redis://:<pass>@localhost:6379/0`.
- Neo4j auth rate limit: wait ~60s or restart the container, ensure all clients use the same password. Healthcheck uses `${NEO4J_AUTH##*/}`.

## Uninstall / teardown

```bash
podman-compose -f deploy/docker/redis/docker-compose.yml down --remove-orphans
podman-compose -f deploy/docker/neo4j/docker-compose.yml down --remove-orphans
```


