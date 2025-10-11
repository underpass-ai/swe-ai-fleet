# Orchestrator Service - Complete Documentation

## 📋 Overview

The Orchestrator Service is a gRPC microservice that coordinates multi-agent deliberation and task execution. It serves as the coordination layer for AI agent teams working collaboratively on software engineering tasks.

**Status:** ✅ API Shell Ready - Awaiting Real Agent Integration

**Port:** 50055  
**Protocol:** gRPC  
**Language:** Python 3.13  
**Pattern:** Domain-Driven Design (DDD)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Orchestrator Service (Port 50055)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Deliberate  │  │ Orchestrate  │  │  GetStatus   │      │
│  │     RPC      │  │     RPC      │  │     RPC      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         ▼                  ▼                  ▼               │
│  ┌────────────────────────────────────────────────────┐     │
│  │         OrchestratorServiceServicer                 │     │
│  ├────────────────────────────────────────────────────┤     │
│  │  • Councils (Role → Deliberate UseCase)            │     │
│  │  • Architect Selector Service                       │     │
│  │  • Scoring Service                                  │     │
│  │  • Stats & Metrics                                  │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ⏳ TODO: Agent Integration                                  │
│  ├─ AgentFactory with LLM backends                          │
│  ├─ Agent Registry/Pool                                     │
│  └─ Dependency Injection                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Deliberation Flow

```
1. Client → Deliberate(task, role, constraints)
   ↓
2. Get council for role (DEV, QA, ARCHITECT, etc.)
   ↓
3. [FUTURE] Agents generate proposals
   ↓
4. [FUTURE] Peer review rounds
   ↓
5. [FUTURE] Scoring & validation
   ↓
6. Return ranked results
```

**Current State:** Returns `UNIMPLEMENTED` until agents are integrated.

## 📡 API Reference

### 1. Deliberate RPC

Execute peer deliberation on a task with a council of agents.

**Request:**
```protobuf
message DeliberateRequest {
  string task_description = 1;    // Task to deliberate on
  string role = 2;                 // DEV, QA, ARCHITECT, DEVOPS, DATA
  TaskConstraints constraints = 3; // Rubric and requirements
  int32 rounds = 4;                // Peer review rounds (default: 1)
  int32 num_agents = 5;            // Agents in council (default: 3)
}
```

**Response:**
```protobuf
message DeliberateResponse {
  repeated DeliberationResult results = 1;  // Ranked proposals
  string winner_id = 2;                     // ID of winning agent
  int64 duration_ms = 3;                    // Execution time
  OrchestratorMetadata metadata = 4;        // Execution metadata
}
```

**Example (grpcurl):**
```bash
grpcurl -plaintext \
  -d '{
    "task_description": "Implement user authentication",
    "role": "DEV",
    "constraints": {
      "rubric": "Secure, maintainable code",
      "requirements": ["Unit tests", "Error handling"]
    },
    "rounds": 1,
    "num_agents": 3
  }' \
  localhost:50055 \
  orchestrator.v1.OrchestratorService/Deliberate
```

**Current Behavior:** Returns `UNIMPLEMENTED` with message:
```
"No agents configured for role: DEV. Agents must be registered before deliberation can occur."
```

### 2. Orchestrate RPC

Execute complete task orchestration workflow (deliberation + architect selection).

**Request:**
```protobuf
message OrchestrateRequest {
  string task_id = 1;              // Unique task identifier
  string task_description = 2;     // Task details
  string role = 3;                 // Role to handle task
  TaskConstraints constraints = 4; // Task constraints
  OrchestratorOptions options = 5; // Orchestration options
}
```

**Response:**
```protobuf
message OrchestrateResponse {
  DeliberationResult winner = 1;            // Selected winner
  repeated DeliberationResult candidates = 2; // All candidates
  string execution_id = 3;                   // Unique execution ID
  int64 duration_ms = 4;                     // Execution time
  OrchestratorMetadata metadata = 5;         // Metadata
}
```

**Current Behavior:** Returns `UNIMPLEMENTED` until agents are configured.

### 3. GetStatus RPC

Get service health and operational statistics.

**Request:**
```protobuf
message GetStatusRequest {
  bool include_stats = 1;  // Include detailed stats
}
```

**Response:**
```protobuf
message GetStatusResponse {
  string status = 1;                // "healthy" or "unhealthy"
  int64 uptime_seconds = 2;         // Service uptime
  OrchestratorStats stats = 3;      // Operational statistics
}
```

**Example:**
```bash
grpcurl -plaintext \
  -d '{"include_stats": true}' \
  localhost:50055 \
  orchestrator.v1.OrchestratorService/GetStatus
```

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "stats": {
    "total_deliberations": 0,
    "total_orchestrations": 0,
    "avg_deliberation_time_ms": 0,
    "active_councils": 0
  }
}
```

## 🚀 Deployment

### Build Container

```bash
# Build (generates APIs automatically inside container)
podman build -t localhost:5000/swe-ai-fleet/orchestrator:v0.1.0 \
  -f services/orchestrator/Dockerfile .

# Push to registry
podman push localhost:5000/swe-ai-fleet/orchestrator:v0.1.0
```

### Deploy to Kubernetes

```bash
# Deploy service
kubectl apply -f deploy/k8s/orchestrator-service.yaml

# Check status
kubectl get pods -n swe -l app=orchestrator
kubectl logs -n swe -l app=orchestrator -f

# Check health
kubectl exec -n swe deployment/orchestrator -- \
  python -c "import grpc; channel = grpc.insecure_channel('localhost:50055'); print('OK')"
```

### Run Locally with Podman

```bash
# Run container
podman run -p 50055:50055 \
  -e GRPC_PORT=50055 \
  -e PYTHONUNBUFFERED=1 \
  localhost:5000/swe-ai-fleet/orchestrator:v0.1.0

# Test with grpcurl
grpcurl -plaintext localhost:50055 \
  orchestrator.v1.OrchestratorService/GetStatus
```

## 🧪 Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/services/orchestrator/ -v -m unit

# With coverage
pytest tests/unit/services/orchestrator/ \
  -v -m unit \
  --cov=services.orchestrator \
  --cov-report=html
```

**Coverage:** 100% of server methods

### Integration Tests

```bash
# Run integration tests (containerized, no local deps)
./scripts/run-integration-tests-podman.sh

# Manual steps
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .
  
podman network create test-net
podman run -d --name orchestrator-test --network test-net \
  localhost:5000/swe-ai-fleet/orchestrator:latest
  
podman build -t test-runner \
  -f tests/integration/services/orchestrator/Dockerfile.test .
  
podman run --rm --network test-net \
  -e ORCHESTRATOR_HOST=orchestrator-test \
  -e ORCHESTRATOR_PORT=50055 \
  test-runner
```

**What They Test:**
- ✅ Service starts successfully
- ✅ gRPC connectivity works
- ✅ All RPC methods respond correctly
- ✅ Error handling is appropriate
- ✅ Health checks function

**What They Don't Test:**
- ⏳ Real agent logic (not implemented yet)
- ⏳ LLM integration
- ⏳ Actual deliberation results

## 🔐 Security

### Container Security

```dockerfile
# Non-root execution
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser
USER appuser
```

### Kubernetes Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
  seccompProfile:
    type: RuntimeDefault
```

### Passing SonarQube

**Common Issues Fixed:**
- ✅ No hardcoded credentials
- ✅ No root execution
- ✅ No privilege escalation
- ✅ Semantic version tags (not :latest)
- ✅ Service account token not auto-mounted
- ✅ No empty implementation stubs

## 📂 File Structure

```
services/orchestrator/
├── server.py              # gRPC server implementation
├── Dockerfile             # Container build (generates APIs)
├── .dockerignore          # Excludes gen/ from build context
├── requirements.txt       # Python dependencies
├── gen/                   # Generated during build (not in git)
│   ├── __init__.py        # Auto-created during build
│   ├── orchestrator_pb2.py
│   ├── orchestrator_pb2_grpc.py
│   └── orchestrator_pb2.pyi
└── README.md              # Service documentation
```

```
tests/integration/services/orchestrator/
├── test_grpc_simple.py         # Simple connectivity tests
├── test_grpc_integration.py    # Full integration tests (Testcontainers)
├── conftest.py                 # Podman/Docker auto-detection
├── Dockerfile.test             # Test runner container
├── docker-compose.test.yml     # Compose file for testing
├── PODMAN_SETUP.md             # Podman configuration guide
└── README.md                   # Integration test documentation
```

```
deploy/k8s/
└── orchestrator-service.yaml   # K8s Service + Deployment + ConfigMap
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC_PORT` | `50055` | gRPC server port |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |

### Kubernetes ConfigMap

```yaml
data:
  config.yaml: |
    service:
      name: orchestrator
      port: 50055
    
    orchestration:
      default_rounds: 1
      default_num_agents: 3
      roles:
        - DEV
        - QA
        - ARCHITECT
        - DEVOPS
        - DATA
```

## 🚧 Current Limitations

### What Works
- ✅ gRPC server starts and accepts connections
- ✅ GetStatus RPC returns service health
- ✅ Proper error handling and logging
- ✅ Container builds with generated APIs
- ✅ Security hardening complete
- ✅ Integration tests pass

### What Needs Implementation
- ⏳ **Agent Creation**: Need AgentFactory with LLM backends
- ⏳ **Councils**: Need to populate councils with real agents
- ⏳ **Deliberation Logic**: Currently returns UNIMPLEMENTED
- ⏳ **Orchestration**: Depends on deliberation
- ⏳ **Persistence**: Results not yet persisted

## 🔌 Integration Guide

### Adding Real Agents

**Option 1: Dependency Injection (Recommended)**

```python
# In server.py
class OrchestratorServiceServicer:
    def __init__(self, config: SystemConfig, agent_factory: AgentFactory):
        self.agent_factory = agent_factory
        
        # Create councils with real agents
        for role_name in ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]:
            agents = self.agent_factory.create_agents(
                role=role_name,
                num_agents=3
            )
            self.councils[role_name] = Deliberate(
                agents=agents,
                tooling=self.scoring,
                rounds=1
            )
```

**Option 2: Agent Registry Service**

```python
# Separate microservice for agents
agent_registry = AgentRegistryClient(host="agents:50060")

for role in ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]:
    agents = await agent_registry.get_agents_for_role(role, count=3)
    servicer.register_council(role, agents)
```

**Option 3: Configuration-Based**

```yaml
# ConfigMap
agents:
  dev:
    - endpoint: "agent-dev-0:50070"
      model: "gpt-4"
    - endpoint: "agent-dev-1:50071"
      model: "claude-3"
  qa:
    - endpoint: "agent-qa-0:50072"
      model: "gpt-4"
```

### Environment Variables for Agents

```bash
# LLM Configuration
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export LLM_MODEL="gpt-4"
export LLM_TEMPERATURE="0.7"

# Agent Configuration
export AGENT_REGISTRY_HOST="agents"
export AGENT_REGISTRY_PORT="50060"
export NUM_AGENTS_PER_ROLE="3"
```

## 📊 Monitoring

### Health Checks

```bash
# Simple health check
grpcurl -plaintext localhost:50055 \
  orchestrator.v1.OrchestratorService/GetStatus

# Kubernetes liveness probe
exec:
  command: ["python", "-c", "import grpc; channel = grpc.insecure_channel('localhost:50055'); channel.close()"]
```

### Metrics (Future)

When agents are integrated, monitor:
- Deliberation success rate
- Average deliberation time
- Agent performance by role
- Proposal quality scores
- Error rates per RPC

### Logs

```bash
# Follow logs
kubectl logs -n swe -l app=orchestrator -f

# Recent errors
kubectl logs -n swe -l app=orchestrator --tail=100 | grep ERROR

# Specific pod
kubectl logs -n swe orchestrator-<pod-id>
```

## 🐛 Troubleshooting

### Service Won't Start

**Check logs:**
```bash
podman logs <container-id>
kubectl logs -n swe deployment/orchestrator
```

**Common issues:**
- Missing dependencies in requirements.txt
- Python path issues (check PYTHONPATH)
- Port already in use
- Protobuf generation failed

### Deliberate Returns UNIMPLEMENTED

**Expected behavior** until agents are integrated.

**To fix:**
1. Implement AgentFactory
2. Inject agents into servicer
3. Register councils with real agents

### Tests Fail

**Integration tests:**
```bash
# Check Podman is running
podman info

# Check socket
ls -la /run/user/$(id -u)/podman/podman.sock

# Rebuild images
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .
```

**Unit tests:**
```bash
# Install dependencies
pip install -e ".[grpc]"

# Run tests
pytest tests/unit/services/orchestrator/ -v
```

## 📈 Performance

### Container Build
- **First build:** ~60 seconds
- **Rebuild (code change):** ~10-15 seconds (with cache mounts)
- **Rebuild (deps change):** ~20-25 seconds

### Service Startup
- **Cold start:** ~2-3 seconds
- **Kubernetes ready:** ~5-10 seconds (with health checks)

### API Response Times (without agents)
- **GetStatus:** <10ms
- **Deliberate:** <5ms (returns UNIMPLEMENTED immediately)
- **Orchestrate:** <5ms (returns UNIMPLEMENTED immediately)

### API Response Times (with agents - estimated)
- **Deliberate:** 2-10 seconds (depends on LLM latency)
- **Orchestrate:** 5-30 seconds (full workflow)

## 🔗 Related Services

| Service | Port | Purpose |
|---------|------|---------|
| Context | 50054 | Provides agent context |
| Planning | 50051 | Task planning |
| Workspace | 50052 | Code execution |
| **Orchestrator** | **50055** | **Agent coordination** |

## 📚 Development

### Generate Protobuf Locally (Optional)

```bash
# Only if you need to test locally before container build
python -m grpc_tools.protoc \
  --proto_path=specs \
  --python_out=services/orchestrator/gen \
  --grpc_python_out=services/orchestrator/gen \
  --pyi_out=services/orchestrator/gen \
  orchestrator.proto

# Fix imports
sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
  services/orchestrator/gen/orchestrator_pb2_grpc.py
```

**Note:** These files are in `.dockerignore` and won't be copied to container.

### Add New RPC Method

1. **Update orchestrator.proto:**
```protobuf
service OrchestratorService {
  rpc NewMethod(NewMethodRequest) returns (NewMethodResponse);
}
```

2. **Regenerate in container** (automatic during build)

3. **Implement in server.py:**
```python
def NewMethod(self, request, context):
    try:
        # Implementation
        return orchestrator_pb2.NewMethodResponse(...)
    except Exception as e:
        context.set_code(grpc.StatusCode.INTERNAL)
        return orchestrator_pb2.NewMethodResponse()
```

4. **Add tests:**
```python
def test_new_method(orchestrator_stub):
    request = orchestrator_pb2.NewMethodRequest(...)
    response = orchestrator_stub.NewMethod(request)
    assert response is not None
```

## 🎯 Roadmap

### Phase 1: API Shell ✅ (Current)
- ✅ Protobuf API definition
- ✅ gRPC server implementation
- ✅ Container builds with API generation
- ✅ Kubernetes deployment
- ✅ Integration tests
- ✅ Documentation

### Phase 2: Agent Integration ⏳ (Next)
- ⏳ AgentFactory implementation
- ⏳ LLM client integration (OpenAI, Anthropic, etc.)
- ⏳ Agent pool management
- ⏳ Real deliberation logic
- ⏳ Scoring implementation

### Phase 3: Production Readiness ⏳ (Future)
- ⏳ Result persistence (Redis/Neo4j)
- ⏳ Metrics and monitoring
- ⏳ Rate limiting
- ⏳ Circuit breakers
- ⏳ Load testing

## 📖 References

- [Protobuf Spec](../../specs/orchestrator.proto)
- [Service README](../../services/orchestrator/README.md)
- [Build Patterns](../MICROSERVICES_BUILD_PATTERNS.md)
- [Integration Tests](../../tests/integration/services/orchestrator/README.md)
- [Podman Setup](../../tests/integration/services/orchestrator/PODMAN_SETUP.md)

## ✅ Summary

The Orchestrator Service is a **fully functional API shell** ready for agent integration. The infrastructure is complete:

- ✅ gRPC API defined and implemented
- ✅ Container builds are reproducible
- ✅ Security hardening applied
- ✅ Tests verify infrastructure
- ✅ Documentation complete

**Next step:** Integrate real AI agents to enable deliberation and orchestration functionality.

