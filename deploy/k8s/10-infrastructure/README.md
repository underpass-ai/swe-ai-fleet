# 10-infrastructure - Core Infrastructure

## Purpose

Core infrastructure services (NATS, databases, caches) required by all microservices.

**Apply second** - After foundation, before microservices.

---

## Files

| File | Resource | Purpose | Dependencies |
|------|----------|---------|--------------|
| `nats.yaml` | StatefulSet + Service | NATS JetStream (messaging backbone) | Secrets |
| `nats-internal-dns.yaml` | 5 Services | Internal DNS aliases for NATS | nats.yaml |
| `neo4j.yaml` | StatefulSet + 2 Services | Neo4j graph database | Secrets (neo4j-auth) |
| `valkey.yaml` | StatefulSet + 3 Services | Valkey cache (Redis-compatible) | None |
| `container-registry.yaml` | Namespace + Deployment + Service + Ingress | Internal container registry | cert-manager |

---

## Apply Order

```bash
# 1. Deploy infrastructure
kubectl apply -f nats.yaml
kubectl apply -f nats-internal-dns.yaml
kubectl apply -f neo4j.yaml
kubectl apply -f valkey.yaml
kubectl apply -f container-registry.yaml

# 2. Wait for readiness (critical)
kubectl wait --for=condition=ready pod -l app=nats -n swe-ai-fleet --timeout=120s
kubectl wait --for=condition=ready pod -l app=neo4j -n swe-ai-fleet --timeout=120s
kubectl wait --for=condition=ready pod -l app=valkey -n swe-ai-fleet --timeout=120s
```

---

## Dependencies

**Requires**:
- ✅ `00-foundation/` applied
- ✅ Secrets created (`neo4j-auth`)
- ✅ cert-manager installed (for container-registry TLS)

**Provides**:
- NATS JetStream (event backbone)
- Neo4j (knowledge graph)
- Valkey (caching layer)
- Container registry (internal image storage)

---

## Verification

```bash
# Check StatefulSets
kubectl get statefulset -n swe-ai-fleet nats neo4j valkey

# Check Services
kubectl get svc -n swe-ai-fleet | grep -E "nats|neo4j|valkey"

# Test connectivity (from within cluster)
kubectl run -it --rm test --image=busybox --restart=Never -n swe-ai-fleet -- /bin/sh -c "
  nc -zv nats.swe-ai-fleet.svc.cluster.local 4222 &&
  nc -zv neo4j.swe-ai-fleet.svc.cluster.local 7687 &&
  nc -zv valkey.swe-ai-fleet.svc.cluster.local 6379
"
```

---

## Ports

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| NATS | 4222 | TCP | Client connections |
| NATS | 6222 | TCP | Cluster routing |
| NATS | 8222 | HTTP | Monitoring |
| Neo4j | 7474 | HTTP | Browser UI |
| Neo4j | 7687 | Bolt | Cypher queries |
| Valkey | 6379 | TCP | Redis protocol |
| Registry | 5000 | HTTP | Docker Registry API |

---

## Troubleshooting

See `docs/operations/K8S_TROUBLESHOOTING.md` for:
- Neo4j OOMKilled issues
- NATS connection problems
- Valkey persistence issues

*** End Patch***}>>;

