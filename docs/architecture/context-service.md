# Context Service

## Overview

The **Context Service** is a Python-based gRPC microservice that implements the Context bounded context from Domain-Driven Design. It provides hydrated prompts to agents based on their role, phase, and the current state of a user story.

## Architecture

### Technology Stack
- **Language**: Python 3.11
- **Protocol**: gRPC
- **Framework**: grpcio
- **Storage**: Neo4j (graph), Redis (planning cache)
- **Port**: 50054

### Domain Model

The Context Service implements the following DDD concepts:

- **Bounded Context**: Context Management
- **Aggregates**: 
  - Case (User Story)
  - Plan Version
  - Decision
  - Subtask
- **Use Cases**:
  - Session Rehydration
  - Prompt Assembly
  - Scope Policy Enforcement
- **Ports**:
  - GraphQueryPort (Neo4j read)
  - GraphCommandPort (Neo4j write)
  - PlanningReadPort (Redis cache)

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│         Context Service (Python gRPC)           │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │    gRPC Server (port 50054)             │  │
│  └──────────────────────────────────────────┘  │
│             │                  │                │
│             ▼                  ▼                │
│  ┌──────────────────┐ ┌──────────────────┐    │
│  │   GetContext     │ │  UpdateContext   │    │
│  └──────────────────┘ └──────────────────┘    │
│             │                  │                │
│             ▼                  ▼                │
│  ┌─────────────────────────────────────────┐   │
│  │   SessionRehydrationUseCase            │   │
│  │   - Rehydrates context from storage    │   │
│  │   - Applies scope policies              │   │
│  │   - Assembles prompt blocks             │   │
│  └─────────────────────────────────────────┘   │
│             │                  │                │
│    ┌────────┴────────┐  ┌──────┴─────────┐    │
│    ▼                 ▼  ▼                ▼     │
│ ┌────────┐      ┌────────┐         ┌────────┐ │
│ │ Neo4j  │      │ Redis  │         │ Policy │ │
│ │ Graph  │      │ Cache  │         │ Engine │ │
│ └────────┘      └────────┘         └────────┘ │
└─────────────────────────────────────────────────┘
```

## API

### GetContext

Retrieves hydrated context for an agent based on story, role, and phase.

**Request:**
```protobuf
message GetContextRequest {
  string story_id = 1;      // User story ID
  string role = 2;          // DEV, QA, DEVOPS, ARCHITECT
  string phase = 3;         // DESIGN, BUILD, TEST, DOCS
  int32 token_budget = 4;   // Optional token limit
}
```

**Response:**
```protobuf
message GetContextResponse {
  string context = 1;       // Hydrated prompt blocks (markdown)
  int32 token_count = 2;    // Estimated token count
}
```

**Example (grpcurl):**
```bash
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "role": "DEV",
  "phase": "BUILD"
}' internal-context:50054 fleet.context.v1.ContextService/GetContext
```

### UpdateContext

Records context changes from agent execution.

**Request:**
```protobuf
message UpdateContextRequest {
  string story_id = 1;
  string task_id = 2;
  repeated ContextChange changes = 3;
}

message ContextChange {
  string entity_type = 1;   // task, decision, artifact, dependency
  string entity_id = 2;
  string operation = 3;     // CREATE, UPDATE, DELETE
  string payload = 4;       // JSON payload
}
```

**Response:**
```protobuf
message UpdateContextResponse {
  int32 version = 1;        // New context version
  string hash = 2;          // Context hash for verification
}
```

**Example (grpcurl):**
```bash
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "task_id": "TASK-001",
  "changes": [{
    "entity_type": "decision",
    "entity_id": "DEC-001",
    "operation": "CREATE",
    "payload": "{\"title\":\"Use Redis for caching\"}"
  }]
}' internal-context:50054 fleet.context.v1.ContextService/UpdateContext
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC_PORT` | `50054` | gRPC server port |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (required) | Neo4j password |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |

### Kubernetes ConfigMap

N/A - Context Service uses environment variables only.

### Secrets

Context Service requires Neo4j credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: neo4j-auth
  namespace: swe-ai-fleet
type: Opaque
data:
  password: <base64-encoded-password>
```

## Deployment

### Prerequisites

1. **Neo4j** must be deployed and accessible
2. **Redis** must be deployed and accessible
3. Container image built and pushed to registry

### Build Image

```bash
cd services
make docker-build-context
make docker-push  # Includes context:v0.1.0
```

### Deploy to Kubernetes

```bash
# Deploy Context Service
./scripts/infra/08-deploy-context.sh

# Or include in full deployment
./scripts/infra/deploy-all.sh
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n swe-ai-fleet -l app=context

# Check service
kubectl get svc -n swe-ai-fleet context

# View logs
kubectl logs -n swe-ai-fleet -l app=context --tail=50 -f

# Test gRPC endpoint
grpcurl -plaintext -d '{
  "story_id": "test",
  "role": "DEV",
  "phase": "BUILD"
}' internal-context:50054 fleet.context.v1.ContextService/GetContext
```

## Monitoring

### Health Checks

- **Liveness Probe**: TCP socket on port 50054
- **Readiness Probe**: TCP socket on port 50054

### Logs

```bash
# View real-time logs
kubectl logs -n swe-ai-fleet -l app=context -f

# Get logs from specific pod
kubectl logs -n swe-ai-fleet context-<pod-id>
```

### Metrics

TODO: Add Prometheus metrics endpoint.

## Development

### Local Development

1. **Install dependencies:**
   ```bash
   cd services/context
   pip install -r requirements.txt
   ```

2. **Generate gRPC code:**
   ```bash
   cd services
   python -m grpc_tools.protoc \
     -I../specs \
     --python_out=./context/gen \
     --pyi_out=./context/gen \
     --grpc_python_out=./context/gen \
     ../specs/context.proto
   ```

3. **Set environment variables:**
   ```bash
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=password
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   ```

4. **Run server:**
   ```bash
   python services/context/server.py
   ```

### Testing

```bash
# Test GetContext
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "role": "DEV",
  "phase": "BUILD"
}' localhost:50054 fleet.context.v1.ContextService/GetContext

# Test UpdateContext
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "task_id": "TASK-001",
  "changes": [{
    "entity_type": "decision",
    "entity_id": "DEC-001",
    "operation": "CREATE",
    "payload": "{}"
  }]
}' localhost:50054 fleet.context.v1.ContextService/UpdateContext
```

## Troubleshooting

### Pod Not Starting

**Symptom:** Pod stuck in `CrashLoopBackOff`

**Diagnosis:**
```bash
kubectl describe pod context-<pod-id> -n swe-ai-fleet
kubectl logs context-<pod-id> -n swe-ai-fleet
```

**Common Causes:**
- Neo4j connection failure (check NEO4J_URI, credentials)
- Redis connection failure (check REDIS_HOST, REDIS_PORT)
- Missing dependencies in container image

### Connection Refused

**Symptom:** `grpcurl` returns connection refused

**Diagnosis:**
```bash
# Check if service is running
kubectl get svc context -n swe-ai-fleet

# Check endpoints
kubectl get endpoints context -n swe-ai-fleet

# Check if pods are ready
kubectl get pods -n swe-ai-fleet -l app=context
```

### Neo4j Connection Issues

**Symptom:** Logs show Neo4j connection errors

**Fix:**
1. Verify Neo4j is running:
   ```bash
   kubectl get pods -n swe-ai-fleet -l app=neo4j
   ```

2. Check Neo4j service:
   ```bash
   kubectl get svc neo4j -n swe-ai-fleet
   ```

3. Verify credentials in secret:
   ```bash
   kubectl get secret neo4j-auth -n swe-ai-fleet -o yaml
   ```

## Integration

### From Planning Service (Go)

```go
import (
    "context"
    contextpb "github.com/underpass-ai/swe-ai-fleet/services/context/gen"
    "google.golang.org/grpc"
)

conn, _ := grpc.Dial("internal-context:50054", grpc.WithInsecure())
client := contextpb.NewContextServiceClient(conn)

req := &contextpb.GetContextRequest{
    StoryId: "USR-001",
    Role:    "DEV",
    Phase:   "BUILD",
}

resp, err := client.GetContext(context.Background(), req)
```

### From Python Agent

```python
import grpc
from gen import context_pb2, context_pb2_grpc

channel = grpc.insecure_channel('internal-context:50054')
stub = context_pb2_grpc.ContextServiceStub(channel)

request = context_pb2.GetContextRequest(
    story_id='USR-001',
    role='DEV',
    phase='BUILD'
)

response = stub.GetContext(request)
print(response.context)
```

## Related Documentation

- [Context Architecture](../../CONTEXT_ARCHITECTURE.md)
- [Domain-Driven Design](../vision/ddd-principles.md)
- [API Specifications](../../specs/context.proto)
- [Deployment Guide](../getting-started/deployment.md)

## Future Enhancements

- [ ] Implement full UpdateContext logic with graph persistence
- [ ] Add Prometheus metrics endpoint
- [ ] Add distributed tracing with OpenTelemetry
- [ ] Implement caching layer for frequently accessed contexts
- [ ] Add support for streaming large contexts
- [ ] Implement context versioning and rollback

