# 30-microservices - Core Application Services

## Purpose

Core microservices implementing the SWE AI Fleet platform.

**Apply fourth** - After infrastructure and streams are ready.

---

## Services

| File | Service | Port | Replicas | Purpose |
|------|---------|------|----------|---------|
| `context.yaml` | Context | 50054 | 2 | Knowledge graph context assembly |
| `orchestrator.yaml` | Orchestrator | 50055 | 2 | Multi-agent deliberation |
| `planning.yaml` | Planning | 50054 | 2 | Story FSM & lifecycle |
| `planning-ceremony-processor.yaml` | Planning Ceremony Processor | 50057 | 1 | gRPC + NATS; ceremony engine execution |
| `workflow.yaml` | Workflow | 50056 | 2 | Task FSM & RBAC Level 2 |
| `workspace.yaml` | Workspace Execution | 50053 | 1 | Sandboxed workspace/tool runtime for agents |
| `workspace-hpa.yaml` | Workspace HPA | - | 1-5 | Horizontal autoscaling profile for workspace |
| `workspace-networkpolicy.yaml` | Workspace NetworkPolicy | - | - | Egress hardening profile for workspace pods |
| `ray-executor.yaml` | Ray Executor | 50056 | 1 | GPU-accelerated agent execution |
| `vllm-server.yaml` | vLLM Server | 8000 | 1 | LLM model serving (Qwen/Llama) |

---

## Apply Order

```bash
# All services can be applied in parallel (no inter-dependencies)
kubectl apply -f context.yaml
kubectl apply -f orchestrator.yaml
kubectl apply -f planning.yaml
kubectl apply -f planning-ceremony-processor.yaml
kubectl apply -f workflow.yaml
kubectl apply -f workspace.yaml
kubectl apply -f workspace-hpa.yaml             # optional autoscaling
kubectl apply -f workspace-networkpolicy.yaml   # recommended for production
kubectl apply -f ray-executor.yaml
kubectl apply -f vllm-server.yaml

# Wait for rollouts (120s timeout recommended)
for svc in context orchestrator planning planning-ceremony-processor workflow workspace ray-executor vllm-server; do
  kubectl rollout status deployment/${svc} -n swe-ai-fleet --timeout=120s
done
```

---

## Dependencies

**Requires**:
- ✅ Foundation applied (`00-foundation/`)
- ✅ Infrastructure running (`10-infrastructure/`)
- ✅ NATS streams created (`20-streams/`)
- ✅ Secrets available (`neo4j-auth`, `huggingface-token`)

---

## Verification

```bash
# Check all microservices
kubectl get pods -n swe-ai-fleet -l component=microservice

# Check readiness
kubectl get pods -n swe-ai-fleet -l 'app in (context,orchestrator,planning,planning-ceremony-processor,workflow,workspace,ray-executor,vllm-server)' \
  -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready

# Check logs for errors
for svc in context orchestrator planning planning-ceremony-processor workflow workspace ray-executor; do
  echo "=== ${svc} ==="
  kubectl logs -n swe-ai-fleet -l app=${svc} --tail=5 | grep -i "error\\|fail\\|exception" || echo "  No errors"
done
```

---

## Service Details

### Context (50054)
- **Purpose**: Assembles surgical context from knowledge graph
- **Dependencies**: Neo4j, Valkey
- **Consumers**: Orchestrator (gRPC client)

### Orchestrator (50055)
- **Purpose**: Multi-agent deliberation and task dispatch
- **Dependencies**: Context (gRPC), Ray Executor (gRPC), NATS
- **Consumers**: Workflow (via NATS events)

### Planning (50054)
- **Purpose**: User story FSM and lifecycle management
- **Dependencies**: Neo4j, Valkey, NATS
- **Consumers**: Workflow (via NATS events)
- **⚠️ Note**: Port fixed from 50053→50054 (2025-11-08)

### Planning Ceremony Processor (50057)
- **Purpose**: gRPC + NATS; ceremony engine execution (`agent.response.completed` consumer)
- **Dependencies**: NATS, Neo4j, Valkey, Ray Executor, vLLM (ConfigMap `service-urls`), Secret `neo4j-auth`
- **Consumers**: Planning (thin client, optional `PLANNING_CEREMONY_PROCESSOR_URL`)
- **Deploy**: Use `make deploy-service SERVICE=planning-ceremony-processor` so the image is built, pushed, and set. Do **not** apply the YAML alone — the manifest references `v0.1.0`, which is never pushed; the deploy script uses `v0.1.0-<timestamp>`.

### Workflow (50056)
- **Purpose**: Task FSM and RBAC Level 2 enforcement
- **Dependencies**: Neo4j, Valkey, NATS
- **Consumers**: Orchestrator (via NATS events)

### Workspace Execution (50053)
- **Purpose**: Run policy-enforced tool calls inside isolated workspaces
- **Dependencies**: none mandatory (local ephemeral volumes by default)
- **Consumers**: Orchestrator / execution runtime callers over HTTP
- **Scaling**: optional HPA in `workspace-hpa.yaml` (CPU/memory driven).
- **Hardening**: apply `workspace-networkpolicy.yaml` to enforce restricted egress.

### Ray Executor (50056)
- **Purpose**: Executes agent tasks on GPU workers
- **Dependencies**: Ray cluster (namespace `ray`)
- **Consumers**: Orchestrator (gRPC client)

### vLLM Server (8000)
- **Purpose**: LLM model serving (OpenAI-compatible API)
- **GPU**: Requires NVIDIA GPU with time-slicing
- **Consumers**: Ray workers (HTTP client)

---

## Troubleshooting

### Service Not Ready

```bash
# Check pod events
kubectl describe pod -n swe-ai-fleet -l app=<service-name>

# Check logs
kubectl logs -n swe-ai-fleet -l app=<service-name> --tail=50

# Common issues:
# - Port mismatch (readiness probe on wrong port)
# - Missing ConfigMap values
# - Database connection timeout
```

### vLLM Server: CrashLoopBackOff / Error 803

If vLLM pods crash with **Error 803** (`unsupported display driver / cuda driver combination`), the host driver is likely newer than the CUDA version in the official image (e.g. driver 590 / CUDA 13.1 vs image built with CUDA 12). See [K8S_TROUBLESHOOTING.md](../K8S_TROUBLESHOOTING.md#-vllm-server-error-803-driver--cuda-mismatch) and [VLLM_CUDA13_BUILD.md](VLLM_CUDA13_BUILD.md) for fixes (driver downgrade or building vLLM with CUDA 13).

If downgrade is not viable, deploy `vllm-server` with a CUDA 13 image override:

```bash
make deploy-service-skip-build SERVICE=vllm-server \
  VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13

kubectl rollout status deployment/vllm-server -n swe-ai-fleet --timeout=120s
kubectl logs -n swe-ai-fleet -l app=vllm-server --tail=50
```

### Planning Ceremony Processor: ImagePullBackOff / CrashLoopBackOff

- **ImagePullBackOff**: The manifest uses `planning-ceremony-processor:v0.1.0`, which is **not** pushed. The deploy script builds and pushes `v0.1.0-<timestamp>`, then runs `kubectl set image`. Always use:
  ```bash
  make deploy-service SERVICE=planning-ceremony-processor
  # or
  make deploy-service-fast SERVICE=planning-ceremony-processor
  ```
  Do **not** only `kubectl apply -f planning-ceremony-processor.yaml`.

- **CrashLoopBackOff**: The app connects to NATS, Neo4j, and Valkey at startup. An **init container** (`wait-deps`) waits for all three before the main container starts. If it still crashes:
  1. Check init container logs: `kubectl logs -n swe-ai-fleet -l app=planning-ceremony-processor -c wait-deps`
  2. Check main container logs: `kubectl logs -n swe-ai-fleet -l app=planning-ceremony-processor -c planning-ceremony-processor --tail=100`
  3. Ensure `service-urls` ConfigMap and `neo4j-auth` Secret exist and NATS / Neo4j / Valkey are running in `10-infrastructure/`.

### Rolling Update

```bash
# Update single service
kubectl set image deployment/<service> <container>=<new-image> -n swe-ai-fleet
kubectl rollout status deployment/<service> -n swe-ai-fleet --timeout=120s

# Rollback if needed
kubectl rollout undo deployment/<service> -n swe-ai-fleet
```
