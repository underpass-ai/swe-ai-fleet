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
| `workflow.yaml` | Workflow | 50056 | 2 | Task FSM & RBAC Level 2 |
| `ray-executor.yaml` | Ray Executor | 50057 | 1 | GPU-accelerated agent execution |
| `vllm-server.yaml` | vLLM Server | 8000 | 1 | LLM model serving (Qwen/Llama) |

---

## Apply Order

```bash
# All services can be applied in parallel (no inter-dependencies)
kubectl apply -f context.yaml
kubectl apply -f orchestrator.yaml
kubectl apply -f planning.yaml
kubectl apply -f workflow.yaml
kubectl apply -f ray-executor.yaml
kubectl apply -f vllm-server.yaml

# Wait for rollouts (120s timeout recommended)
for svc in context orchestrator planning workflow ray-executor vllm-server; do
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

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Planning   │────▶│  Workflow    │────▶│Orchestrator │
│   (50054)   │     │   (50056)    │     │   (50055)   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                    │
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────┐
│              NATS JetStream (Events)                │
└─────────────────────────────────────────────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Context   │     │ Ray Executor │────▶│  vLLM       │
│   (50054)   │     │   (50057)    │     │  (8000)     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                         │
       └────────────────┬────────────────────────┘
                        ▼
              ┌──────────────────┐
              │ Neo4j + Valkey   │
              └──────────────────┘
```

---

## Verification

```bash
# Check all microservices
kubectl get pods -n swe-ai-fleet -l component=microservice

# Check readiness
kubectl get pods -n swe-ai-fleet -l 'app in (context,orchestrator,planning,workflow,ray-executor,vllm-server)' \
  -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready

# Check logs for errors
for svc in context orchestrator planning workflow ray-executor; do
  echo "=== ${svc} ==="
  kubectl logs -n swe-ai-fleet -l app=${svc} --tail=5 | grep -i "error\|fail\|exception" || echo "  No errors"
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

### Workflow (50056)
- **Purpose**: Task FSM and RBAC Level 2 enforcement
- **Dependencies**: Neo4j, Valkey, NATS
- **Consumers**: Orchestrator (via NATS events)

### Ray Executor (50057)
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

### Rolling Update

```bash
# Update single service
kubectl set image deployment/<service> <container>=<new-image> -n swe-ai-fleet
kubectl rollout status deployment/<service> -n swe-ai-fleet --timeout=120s

# Rollback if needed
kubectl rollout undo deployment/<service> -n swe-ai-fleet
```

