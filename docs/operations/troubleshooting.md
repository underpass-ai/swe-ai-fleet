# 🔧 Troubleshooting Guide

> **Comprehensive Reference**: Kubernetes (K8s) + CRI-O operational troubleshooting
> Combines K8S_TROUBLESHOOTING + TROUBLESHOOTING_CRIO into single canonical source

---

## 🚀 Quick Diagnostics

### Kubernetes Cluster

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

### CRI-O & Containers

```bash
# List containers
sudo crictl ps -a --name neo4j

# View logs
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl logs "$CID" --tail=200

# Execute into container
sudo crictl exec "$CID" /bin/sh -c "env | grep NEO4J"

# Get container status
sudo crictl ps "$CID" -o json | jq '.containers[0].state'
```

---

## 🔴 Kubernetes Issues

### Issue A: Neo4j CrashLoopBackOff – Bad Config Key

**Symptoms:**
```
Error: Unrecognized setting: server.config.strict_validation_enabled
```

**Cause:** Wrong env mapping. Correct property is `server.config.strict_validation.enabled`.

**Fix:**
```bash
# Remove wrong env var and ensure overrides are enabled
kubectl -n swe set env deploy/neo4j NEO4J_server_config_strict__validation__enabled-
kubectl -n swe set env deploy/neo4j NEO4J_server_config_override__with__environment=true
# Set the correct var (false while fixing; set true later for prod)
kubectl -n swe set env deploy/neo4j NEO4J_server_config_strict__validation_enabled=false
```

**Best Practice:**
```bash
# Avoid service env collisions
kubectl -n swe patch deploy/neo4j -p '{"spec":{"template":{"spec":{"enableServiceLinks":false}}}}'
```

---

### Issue B: Neo4j OOMKilled (Exit Code 137)

**Symptoms:**
- `OOMKilled` status
- Frequent restarts within seconds
- Container exits with code 137

**Cause:** 1Gi limit without explicit heap/pagecache sizing

**Fix (Fits in 2Gi):**
```bash
kubectl -n swe patch deploy/neo4j --type merge -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "neo4j",
            "resources": {
              "requests": {"cpu": "500m", "memory": "1Gi"},
              "limits": {"cpu": "1", "memory": "2Gi"}
            },
            "env": [
              {"name": "NEO4J_server_memory_heap_initial__size", "value": "1G"},
              {"name": "NEO4J_server_memory_heap_max__size", "value": "1G"},
              {"name": "NEO4J_server_memory_pagecache__size", "value": "512M"}
            ],
            "startupProbe": {"tcpSocket": {"port": 7687}, "periodSeconds": 10, "failureThreshold": 60},
            "readinessProbe": {"tcpSocket": {"port": 7474}, "initialDelaySeconds": 15, "periodSeconds": 5, "timeoutSeconds": 5, "failureThreshold": 60},
            "livenessProbe": {"tcpSocket": {"port": 7687}, "initialDelaySeconds": 60, "periodSeconds": 10, "timeoutSeconds": 5, "failureThreshold": 30}
          }
        ]
      }
    }
  }
}'

# Rollout with 120s waits
kubectl -n swe rollout restart deploy/neo4j
kubectl -n swe rollout status deploy/neo4j --timeout=120s | cat
```

**If Stuck with 1Gi Limit:**
```bash
# Reduce heap and pagecache
neo4j_server_memory_heap_initial__size=512M
neo4j_server_memory_heap_max__size=512M
neo4j_server_memory_pagecache__size=256M
```

---

### Issue C: Rollout Timeouts – Old Replica Pending Termination

**Symptoms:**
- `kubectl rollout status` times out
- Old pods not terminating
- Deadlock between old and new replicas

**Fix:**
```bash
kubectl -n swe scale deploy/neo4j --replicas=0
kubectl -n swe wait --for=delete pod -l app=neo4j --timeout=120s
kubectl -n swe scale deploy/neo4j --replicas=1
kubectl -n swe rollout status deploy/neo4j --timeout=120s | cat
```

---

### Issue D: ImagePullBackOff / I/O Timeout

**Symptoms:**
```
ImagePullBackOff
Failed to pull image "docker.io/neo4j:5.26.12": rpc error: code = Unknown desc = context deadline exceeded
```

**Cause:** Cloudflare R2 or docker.io timeout

**Option A: Use Cached Tag**
```bash
kubectl -n swe set image deploy/neo4j neo4j=docker.io/neo4j:5
```

**Option B: Use Google Mirror**
```bash
kubectl -n swe set image deploy/neo4j neo4j=mirror.gcr.io/library/neo4j:5.26.12
```

**Option C: Pre-pull into CRI-O Cache**
```bash
# On internet-connected host:
skopeo copy \
  docker://docker.io/neo4j:5.26.12 \
  docker-archive:/tmp/neo4j-5.26.12.tar:neo4j:5.26.12

# Transfer tar to node, then:
sudo skopeo copy \
  docker-archive:/tmp/neo4j-5.26.12.tar \
  containers-storage:docker.io/library/neo4j:5.26.12

# Verify
sudo crictl images | grep neo4j
```

**Network Diagnostics:**
```bash
# On node with issue
curl -I --connect-timeout 5 https://registry-1.docker.io/v2/ || echo "docker.io FAIL"
curl -I --connect-timeout 5 https://docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com/ || echo "Cloudflare FAIL"
```

---

### Issue E: Secrets Validation

**Symptoms:**
- Pod can't authenticate to database
- Environment variables for credentials not set

**Check Secrets:**
```bash
kubectl -n swe get secrets
kubectl -n swe get secret redis-auth  -o jsonpath='{.data.password}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.username}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.password}' | wc -c
kubectl -n swe get secret neo4j-auth  -o jsonpath='{.data.auth}' | wc -c
```

**Expected:**
- `redis-auth` has key `password`
- `neo4j-auth` has keys `username`, `password`, `auth`

**Create Missing Secrets:**
```bash
# Redis auth
kubectl create secret generic redis-auth \
  --from-literal=password=swefleet-dev \
  -n swe --dry-run=client -o yaml | kubectl apply -f -

# Neo4j auth
kubectl create secret generic neo4j-auth \
  --from-literal=username=neo4j \
  --from-literal=password=swefleet-dev \
  --from-literal=auth=neo4j:swefleet-dev \
  -n swe --dry-run=client -o yaml | kubectl apply -f -
```

---

### Issue F: ContainerStatusUnknown After Node/Workstation Restart

**Symptoms:**
- Pods stuck in `ContainerStatusUnknown` status
- After server/workstation reboot
- Typically affects GPU workloads (vllm-server) or long-running pods

**Cause:** kubelet lost track of container state during restart

**Fix:**
```bash
# Restart the affected service
kubectl scale deployment/vllm-server -n swe-ai-fleet --replicas=0
kubectl wait --for=delete pod -l app=vllm-server -n swe-ai-fleet --timeout=60s
kubectl scale deployment/vllm-server -n swe-ai-fleet --replicas=1

# Verify new pod starts correctly
kubectl get pods -n swe-ai-fleet -l app=vllm-server -w
```

**Prevention:**
```yaml
# In pod spec
terminationGracePeriodSeconds: 30
livenessProbe:
  tcpSocket:
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  tcpSocket:
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 5
```

**When This Occurs:**
- After node reboot/restart ✅
- After containerd/CRI-O restart ✅
- After network disruption on node ✅
- After GPU driver reload ✅

**Affected Pods:**
- vllm-server (GPU workloads)
- Long-running stateful services
- Pods without proper health checks

---

## 🔴 CRI-O & Local Container Issues

### vLLM: Failed to Infer Device Type

**Symptoms:**
```
RuntimeError: Failed to infer device type
```

**Fix:**
```bash
# Regenerate CDI without /dev/dri paths and restart CRI-O
sudo nvidia-ctk cdi generate \
  --output=/etc/cdi/nvidia.yaml \
  --format=yaml \
  --csv.ignore-pattern '/dev/dri/.*'

sudo systemctl restart crio
```

**Use Correct Runtime:**
```bash
# Use nvidia runtime handler
sudo crictl runp --runtime nvidia deploy/crio/vllm-pod.json

# Set environment variables in container JSON
# VLLM_DEVICE=cuda
# NVIDIA_VISIBLE_DEVICES=all
# CUDA_VISIBLE_DEVICES=0,1
```

---

### CDI: Device Injection Errors (DRM Paths)

**Symptoms:**
```
Error: /dev/dri/card0 not found
Error: /dev/dri/renderD128 not found
```

**Fix:**
```bash
# Regenerate CDI excluding /dev/dri paths (see vLLM issue above)
sudo nvidia-ctk cdi generate \
  --output=/etc/cdi/nvidia.yaml \
  --format=yaml \
  --csv.ignore-pattern '/dev/dri/.*'

sudo systemctl restart crio
```

---

### CRI-O: Unknown Flag --hooks-dir-path

**Symptoms:**
```
Error: unknown flag: --hooks-dir-path
```

**Fix:**
```bash
# Remove --hooks-dir-path and use CDI instead
# Either use device syntax:
sudo crictl runp --device nvidia.com/gpu=all pod.json

# Or use runtime handler:
sudo crictl runp --runtime nvidia pod.json
```

---

### CRI-O Permissions (crictl)

**Symptoms:**
```
permission denied connecting to /run/crio/crio.sock
```

**Fix:**
```bash
# Use sudo
sudo crictl ps

# Or add user to appropriate group (requires relogin)
sudo usermod -aG crio $USER
sudo usermod -aG kvm $USER
# Then: exit and log back in
```

---

### Neo4j Authentication / Initial Password

**Symptoms:**
```
Unauthorized
AuthenticationRateLimit
```

**Fix (CRI-O):**
```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec "$CID" /var/lib/neo4j/bin/cypher-shell \
  -d system -u neo4j -p neo4j \
  "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'swefleet-dev'"
```

**If Multiple Auth Failures:**
- Wait 30 seconds between attempts
- Check system time (NTP may be off)
- Verify user exists: `CALL dbms.security.listUsers()`

---

### vLLM Network Timeouts to Hugging Face

**Symptoms:**
```
NameResolutionError: huggingface.co
ConnectionTimeout: Connection to huggingface.co timed out
```

**Fix:**
```bash
# Option A: Use host network for pod
# Set "network_mode": "host" in pod JSON

# Option B: Pre-populate HF cache on host
mkdir -p /data/huggingface-cache
export HF_HOME=/data/huggingface-cache

# Download model locally
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2-7B-Instruct')"

# Mount into container at /root/.cache/huggingface
# In pod JSON: "volumeMounts": [{"name": "hf-cache", "mountPath": "/root/.cache/huggingface"}]
```

---

### Python 3.13 vs PyTorch/vLLM

**Symptoms:**
```
No matching distribution found for torch
Wheel not available for Python 3.13
```

**Fix:**
- Use **Python 3.11** for local vLLM installs
- Use **upstream vLLM container images** (they handle version compatibility)

---

### Redis Connection Refused

**Symptoms:**
```
Error 111 connecting to localhost:6379
Connection refused
```

**Fix:**
```bash
# Ensure Redis pod is running with host network
sudo crictl ps -a --name redis

# Verify password is set
redis-cli -a swefleet-dev PING

# Check if listening
sudo crictl exec $CID redis-cli CONFIG GET requirepass
```

---

## 📋 Policy: Rollout Timeouts

**Standard timeout for all rollout operations:**
```bash
--timeout=120s
```

Use this consistently in all scripts:
- `kubectl rollout status`
- `kubectl wait --for=...`
- `kubectl scale`

---

## 🆘 When All Else Fails

### Nuclear Option: Full Reset

```bash
# Delete entire namespace and recreate
kubectl delete namespace swe-ai-fleet
kubectl wait --for=delete namespace/swe-ai-fleet --timeout=120s

# Recreate from scratch
./scripts/infra/fresh-redeploy.sh --reset-nats
```

### Collect Diagnostics for Support

```bash
# Collect all pod logs
mkdir -p /tmp/debug
kubectl logs -n swe-ai-fleet -l app=neo4j > /tmp/debug/neo4j.log
kubectl logs -n swe-ai-fleet -l app=redis > /tmp/debug/redis.log
kubectl describe pods -n swe-ai-fleet > /tmp/debug/pods.txt
kubectl get events -n swe-ai-fleet > /tmp/debug/events.txt

# Archive for sharing
tar -czf swe-debug-$(date +%s).tar.gz /tmp/debug/
```

---

## 🔗 Related Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment procedures
- [Getting Started](../getting-started/README.md) - Initial setup
- [Monitoring](../monitoring/OBSERVABILITY_SETUP.md) - Health monitoring

---

**Status**: ✅ **CANONICAL REFERENCE**
**Coverage**: Kubernetes + CRI-O + GPU
**Last Updated**: 2025-11-15


