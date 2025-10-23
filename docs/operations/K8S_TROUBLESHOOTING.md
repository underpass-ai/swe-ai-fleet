# Kubernetes Troubleshooting (Demo Stack)

This guide captures issues seen while deploying the demo (Redis, Neo4j, Frontend) on Kubernetes. Default waits: use rollout/wait timeouts ≤120s.

## Quick diagnostics

```bash
# Namespace summary
kubectl -n swe get all,ingress,secrets,events

# Focus on a component
kubectl -n swe get deploy,rs,pod -l app=neo4j -o wide
kubectl -n swe describe pod -l app=neo4j | sed -n '/Events:/,$p'

# Logs
kubectl -n swe logs deploy/neo4j --tail=200 | cat
kubectl -n swe logs -l app=neo4j --tail=200 --prefix | cat
kubectl -n swe logs -l app=neo4j --previous --tail=200 | cat

# Pod internals
POD=$(kubectl -n swe get pod -l app=neo4j -o jsonpath='{.items[0].metadata.name}')
kubectl -n swe get pod "$POD" -o jsonpath='{.status.containerStatuses[0].state}{"\n"}{.status.containerStatuses[0].lastState}{"\n"}' | cat
kubectl -n swe exec "$POD" -- env | sort | grep -E 'NEO4J|STRICT|OVERRIDE'
kubectl -n swe exec "$POD" -- sh -lc 'ss -lntp || netstat -lntp' | grep -E '(:7474|:7687)' || true
kubectl -n swe exec "$POD" -- sh -lc 'ls -lah /logs && tail -n 200 /logs/debug.log || true'

# Rollout helpers (120s max)
kubectl -n swe rollout status deploy/neo4j --timeout=120s | cat
kubectl -n swe scale deploy/neo4j --replicas=0 && \
  kubectl -n swe wait --for=delete pod -l app=neo4j --timeout=120s && \
  kubectl -n swe scale deploy/neo4j --replicas=1
```

---

## Issue A: Neo4j CrashLoopBackOff – bad config key (strict validation)

- Symptoms: `Unrecognized setting: server.config.strict_validation_enabled`.
- Cause: wrong env mapping. Correct property is `server.config.strict_validation.enabled`.
- Fix:

```bash
# Remove wrong env var and ensure overrides are enabled
kubectl -n swe set env deploy/neo4j NEO4J_server_config_strict__validation__enabled-
kubectl -n swe set env deploy/neo4j NEO4J_server_config_override__with__environment=true
# Set the correct var (false while fixing; set true later for prod)
kubectl -n swe set env deploy/neo4j NEO4J_server_config_strict__validation_enabled=false
```

Tip: set `enableServiceLinks: false` in the pod spec to avoid service env collisions.

---

## Issue B: Neo4j OOMKilled (exitCode 137)

- Symptoms: `OOMKilled`, frequent restarts within seconds.
- Cause: 1Gi limit without explicit heap/pagecache sizing.
- Fix (fits in 2Gi):

```bash
# Increase limits and pin memory settings explicitly
kubectl -n swe patch deploy/neo4j --type merge -p '
{"spec":{"template":{"spec":{"containers":[{"name":"neo4j",
  "resources":{"requests":{"cpu":"500m","memory":"1Gi"},"limits":{"cpu":"1","memory":"2Gi"}},
  "env":[
    {"name":"NEO4J_server_memory_heap_initial__size","value":"1G"},
    {"name":"NEO4J_server_memory_heap_max__size","value":"1G"},
    {"name":"NEO4J_server_memory_pagecache__size","value":"512M"}
  ],
  "startupProbe":{"tcpSocket":{"port":7687},"periodSeconds":10,"failureThreshold":60},
  "readinessProbe":{"tcpSocket":{"port":7474},"initialDelaySeconds":15,"periodSeconds":5,"timeoutSeconds":5,"failureThreshold":60},
  "livenessProbe":{"tcpSocket":{"port":7687},"initialDelaySeconds":60,"periodSeconds":10,"timeoutSeconds":5,"failureThreshold":30}
}]}}}}'

# Rollout with 120s waits
kubectl -n swe rollout restart deploy/neo4j
kubectl -n swe rollout status deploy/neo4j --timeout=120s | cat
```

If you must keep 1Gi limit: set heap=512M and pagecache=256M.

---

## Issue C: Rollout timeouts – old replica pending termination

```bash
kubectl -n swe scale deploy/neo4j --replicas=0
kubectl -n swe wait --for=delete pod -l app=neo4j --timeout=120s
kubectl -n swe scale deploy/neo4j --replicas=1
kubectl -n swe rollout status deploy/neo4j --timeout=120s | cat
```

---

## Issue D: ImagePullBackOff / i/o timeout (docker.io/neo4j:5.26.12)

- Symptoms: Cloudflare R2 i/o timeouts; `ImagePullBackOff`.
- Options:

```bash
# A) Use cached tag if present
kubectl -n swe set image deploy/neo4j neo4j=docker.io/neo4j:5

# B) Use Google mirror for exact pin
kubectl -n swe set image deploy/neo4j neo4j=mirror.gcr.io/library/neo4j:5.26.12

# C) Pre-pull offline into CRI-O cache (on node)
# On host with Internet:
#   skopeo copy docker://docker.io/neo4j:5.26.12 docker-archive:/tmp/neo4j-5.26.12.tar:neo4j:5.26.12
# Transfer tar to node, then:
sudo skopeo copy docker-archive:/tmp/neo4j-5.26.12.tar containers-storage:docker.io/library/neo4j:5.26.12
sudo crictl images | grep neo4j
```

Network checks (on node):

```bash
curl -I --connect-timeout 5 https://registry-1.docker.io/v2/ || echo FAIL
curl -I --connect-timeout 5 https://docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com/ || echo FAIL
```

---

## Issue E: Secrets validation

```bash
kubectl -n swe get secrets
kubectl -n swe get secret redis-auth  -o jsonpath='{.data.password}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.username}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.password}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.auth}'     | wc -c
```

Expected: `redis-auth` has `password`; `neo4j-auth` has `username`, `password`, `auth`.

---

## Issue F: `ContainerStatusUnknown` after node/workstation restart

**Symptoms:**
- Pods stuck in `ContainerStatusUnknown` status after server/workstation reboot
- Typically affects GPU workloads (vllm-server) or long-running pods
- `kubectl get pods` shows status but pods are not actually running

**Cause:** kubelet lost track of container state during node restart

**Fix:**
```bash
# Affected service (example: vllm-server)
kubectl scale deployment/vllm-server -n swe-ai-fleet --replicas=0
kubectl wait --for=delete pod -l app=vllm-server -n swe-ai-fleet --timeout=60s
kubectl scale deployment/vllm-server -n swe-ai-fleet --replicas=1

# Verify new pod starts correctly
kubectl get pods -n swe-ai-fleet -l app=vllm-server -w
```

**Prevention:**
- Set `terminationGracePeriodSeconds: 30` in pod spec
- Use liveness/readiness probes for automatic recovery
- Consider PodDisruptionBudgets for critical services

**When this happens:**
- ✅ After node reboot/restart
- ✅ After containerd/CRI-O restart
- ✅ After network disruption on node
- ✅ After GPU driver reload

**Affected pods typically:**
- vllm-server (GPU workloads)
- Long-running stateful services
- Pods without proper health checks

---

## Policy: rollout/status timeouts

Use `--timeout=120s` as the default for `kubectl rollout status` and `kubectl wait`.
