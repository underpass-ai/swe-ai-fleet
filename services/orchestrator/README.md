# Orchestrator Service

Python-based gRPC microservice for multi-agent deliberation and task orchestration.

## 🎯 Purpose

The Orchestrator Service coordinates multi-agent deliberation and task execution through:
- **Peer deliberation** - Multiple agents propose and review solutions
- **Task orchestration** - Complete workflow from task to selected solution
- **Architect selection** - Best proposal selection based on checks and scoring
- **Role-based councils** - Specialized agent teams for different roles

## 🏗️ Architecture

- **Protocol**: gRPC (port 50055)
- **Language**: Python 3.13
- **Pattern**: Domain-Driven Design (DDD) with Clean Architecture
- **Agents**: Multi-agent peer review system
- **Scoring**: Automated checks (policy, lint, dry-run)

## 📁 Structure

```
orchestrator/
├── server.py              # gRPC server
├── Dockerfile             # Container image definition
├── requirements.txt       # Python dependencies
├── gen/                   # Generated gRPC code
│   ├── orchestrator_pb2.py
│   ├── orchestrator_pb2_grpc.py
│   └── orchestrator_pb2.pyi
└── README.md
```

## 🚀 Quick Start

### Build

```bash
# Build Docker image
docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest -f services/orchestrator/Dockerfile .

# Push to local registry
docker push localhost:5000/swe-ai-fleet/orchestrator:latest
```

### Run Locally

```bash
# Install dependencies
pip install -r services/orchestrator/requirements.txt

# Set environment variables
export GRPC_PORT=50055

# Run server
python services/orchestrator/server.py
```

### Deploy to Kubernetes

```bash
# Deploy
kubectl apply -f deploy/k8s/orchestrator-service.yaml

# Check status
kubectl get pods -n swe -l app=orchestrator
kubectl logs -n swe -l app=orchestrator -f
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC_PORT` | `50055` | gRPC server port |
| `PYTHONUNBUFFERED` | `1` | Python unbuffered output |

## 📡 API Methods

### Deliberate

Execute peer deliberation on a task with a council of agents.

**Request:**
```protobuf
message DeliberateRequest {
  string task_description = 1;
  string role = 2;  // DEV, QA, ARCHITECT, etc.
  TaskConstraints constraints = 3;
  int32 rounds = 4;  // Peer review rounds
  int32 num_agents = 5;  // Agents in council
}
```

**Response:**
```protobuf
message DeliberateResponse {
  repeated DeliberationResult results = 1;  // Ranked proposals
  string winner_id = 2;
  int64 duration_ms = 3;
}
```

### Orchestrate

Execute complete task orchestration workflow.

**Request:**
```protobuf
message OrchestrateRequest {
  string task_id = 1;
  string task_description = 2;
  string role = 3;
  TaskConstraints constraints = 4;
}
```

**Response:**
```protobuf
message OrchestrateResponse {
  DeliberationResult winner = 1;
  repeated DeliberationResult candidates = 2;
  string execution_id = 3;
}
```

### GetStatus

Get service health and statistics.

**Request:**
```protobuf
message GetStatusRequest {
  bool include_stats = 1;
}
```

**Response:**
```protobuf
message GetStatusResponse {
  string status = 1;
  int64 uptime_seconds = 2;
  OrchestratorStats stats = 3;
}
```

## 🔍 Health Checks

### Liveness Probe
```bash
python -c "import grpc; channel = grpc.insecure_channel('localhost:50055'); channel.close()"
```

### Check with grpcurl
```bash
grpcurl -plaintext localhost:50055 orchestrator.v1.OrchestratorService/GetStatus
```

## 🔒 Security Features

- **Non-root execution** - Runs as UID 1000
- **Read-only root filesystem** - Immutable container
- **No privilege escalation** - Restricted capabilities
- **Seccomp profile** - Syscall filtering
- **Resource limits** - CPU and memory constraints

## 📊 Monitoring

### Key Metrics
- Total deliberations
- Total orchestrations
- Average execution time
- Active councils
- Role distribution

### Logs
```bash
# Follow logs
kubectl logs -n swe -l app=orchestrator -f

# Get recent logs
kubectl logs -n swe -l app=orchestrator --tail=100
```

## 🧪 Development

### Generate gRPC Code
```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=services/orchestrator/gen \
  --grpc_python_out=services/orchestrator/gen \
  --pyi_out=services/orchestrator/gen \
  specs/orchestrator.proto
```

### Run Tests
```bash
pytest tests/unit/services/orchestrator/ -v
```

## 🔗 Related Services

- **Context Service** (port 50054) - Provides agent context
- **Planning Service** (port 50051) - Task planning
- **Workspace Service** (port 50052) - Code execution

## 📚 Architecture

The Orchestrator Service implements a **multi-agent deliberation pattern**:

1. **Proposal Generation** - Agents independently generate solutions
2. **Peer Review** - Agents critique each other's proposals
3. **Revision** - Proposals are revised based on feedback
4. **Scoring** - Automated checks evaluate proposals
5. **Selection** - Architect chooses best proposal

This ensures high-quality solutions through collaborative intelligence.

