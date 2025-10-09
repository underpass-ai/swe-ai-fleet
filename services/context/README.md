# Context Service

Python-based gRPC microservice for intelligent context management and hydration.

## 🎯 Purpose

The Context Service provides hydrated, role-specific context to AI agents based on:
- **User story state** and lifecycle
- **Agent role** (DEV, QA, ARCHITECT, DEVOPS, DATA)
- **Execution phase** (DESIGN, BUILD, TEST, DOCS)
- **Scope policies** (security, token budgets, information filtering)

## 🏗️ Architecture

- **Protocol**: gRPC (port 50054) + NATS async messaging
- **Language**: Python 3.11+
- **Storage**: 
  - Neo4j (decision graph, long-term)
  - Redis (planning data, short-term)
- **Pattern**: Domain-Driven Design (DDD) with Clean Architecture
- **Messaging**: NATS JetStream for async events

## 📁 Structure

```
context/
├── server.py              # gRPC server with NATS support
├── nats_handler.py        # NATS event handler
├── Dockerfile             # Container image definition
├── requirements.txt       # Python dependencies
├── gen/                   # Generated gRPC code
│   ├── context_pb2.py
│   ├── context_pb2_grpc.py
│   └── context_pb2.pyi
└── README.md
```

## 🚀 Quick Start

### Build

```bash
# Build Docker image
make context-build

# Or manually
docker build -t localhost:5000/swe-ai-fleet/context:latest -f services/context/Dockerfile .
```

### Run Locally

```bash
# Install dependencies
pip install -r services/context/requirements.txt

# Set environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_PASSWORD=your-password
export REDIS_HOST=localhost
export NATS_URL=nats://localhost:4222

# Run server
python services/context/server.py
```

### Deploy to Kubernetes

```bash
# Deploy with script
./scripts/infra/deploy-context.sh

# Or manually
kubectl apply -f deploy/k8s/context-service.yaml

# Check status
kubectl get pods -n swe -l app=context
kubectl logs -n swe -l app=context -f
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC_PORT` | `50054` | gRPC server port |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (required) | Neo4j password |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `NATS_URL` | `nats://nats:4222` | NATS server URL |
| `ENABLE_NATS` | `true` | Enable NATS messaging |

### Kubernetes Resources

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

## 📡 API Reference

### gRPC Methods

#### 1. GetContext

Retrieve hydrated context for an agent.

**Request:**
```protobuf
message GetContextRequest {
  string story_id = 1;
  string role = 2;        // DEV, QA, ARCHITECT, etc.
  string phase = 3;       // DESIGN, BUILD, TEST, DOCS
  string subtask_id = 4;  // Optional: focus on specific subtask
  int32 token_budget = 5; // Optional: token budget hint
}
```

**Response:**
```protobuf
message GetContextResponse {
  string context = 1;           // Formatted context string
  int32 token_count = 2;        // Estimated token count
  repeated string scopes = 3;   // Applied scope policies
  string version = 4;           // Context version/hash
  PromptBlocks blocks = 5;      // Structured prompt blocks
}
```

**Example:**
```bash
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "role": "DEV",
  "phase": "BUILD"
}' localhost:50054 fleet.context.v1.ContextService/GetContext
```

#### 2. UpdateContext

Record context changes from agent execution.

**Request:**
```protobuf
message UpdateContextRequest {
  string story_id = 1;
  string task_id = 2;
  string role = 3;
  repeated ContextChange changes = 4;
  string timestamp = 5;
}
```

**Response:**
```protobuf
message UpdateContextResponse {
  int32 version = 1;
  string hash = 2;
  repeated string warnings = 3;
}
```

**Example:**
```bash
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "task_id": "TASK-001",
  "role": "DEV",
  "changes": [{
    "operation": "CREATE",
    "entity_type": "DECISION",
    "entity_id": "DEC-001",
    "payload": "{\"title\":\"Use PostgreSQL\"}",
    "reason": "Performance requirements"
  }]
}' localhost:50054 fleet.context.v1.ContextService/UpdateContext
```

#### 3. RehydrateSession

Rebuild context from persistent storage.

**Request:**
```protobuf
message RehydrateSessionRequest {
  string case_id = 1;
  repeated string roles = 2;
  bool include_timeline = 3;
  bool include_summaries = 4;
  int32 timeline_events = 5;
  bool persist_bundle = 6;
  int32 ttl_seconds = 7;
}
```

**Response:**
```protobuf
message RehydrateSessionResponse {
  string case_id = 1;
  int64 generated_at_ms = 2;
  map<string, RoleContextPack> packs = 3;
  RehydrationStats stats = 4;
}
```

**Example:**
```bash
grpcurl -plaintext -d '{
  "case_id": "CASE-001",
  "roles": ["DEV", "QA"],
  "include_timeline": true,
  "include_summaries": true
}' localhost:50054 fleet.context.v1.ContextService/RehydrateSession
```

#### 4. ValidateScope

Check if provided scopes are allowed for role/phase.

**Request:**
```protobuf
message ValidateScopeRequest {
  string role = 1;
  string phase = 2;
  repeated string provided_scopes = 3;
}
```

**Response:**
```protobuf
message ValidateScopeResponse {
  bool allowed = 1;
  repeated string missing = 2;
  repeated string extra = 3;
  string reason = 4;
}
```

### NATS Events

#### Subscriptions

- `context.update.request` - Context update requests
- `context.rehydrate.request` - Session rehydration requests

#### Publications

- `context.update.response` - Update responses
- `context.rehydrate.response` - Rehydration responses
- `context.events.updated` - Context updated events

**Example Event:**
```json
{
  "event_type": "context.updated",
  "story_id": "USR-001",
  "version": 2,
  "timestamp": 1234567890.123
}
```

## 🧪 Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/context/ -v

# With coverage
pytest tests/unit/context/ --cov=swe_ai_fleet.context --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires services)
pytest tests/integration/test_context_service.py -v -m integration

# Run e2e tests
pytest tests/integration/test_context_service.py -v -m e2e
```

### Manual Testing

```bash
# Port forward service
kubectl port-forward -n swe svc/context 50054:50054

# Test with grpcurl
grpcurl -plaintext \
  -d '{"story_id":"test","role":"DEV","phase":"BUILD"}' \
  localhost:50054 \
  fleet.context.v1.ContextService/GetContext
```

## 📊 Monitoring

### Health Checks

```bash
# Liveness probe
python -c "import grpc; channel = grpc.insecure_channel('localhost:50054'); channel.close()"

# Readiness probe
kubectl get pods -n swe -l app=context
```

### Logs

```bash
# View logs
kubectl logs -n swe -l app=context -f

# View logs for specific pod
kubectl logs -n swe context-<pod-id> -f

# View NATS-related logs
kubectl logs -n swe -l app=context -f | grep NATS
```

### Metrics

```bash
# Pod metrics
kubectl top pods -n swe -l app=context

# Service endpoints
kubectl get endpoints -n swe context
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Neo4j Connection Failed

```
Error: Failed to connect to Neo4j
```

**Solution:**
- Check Neo4j is running: `kubectl get pods -n swe -l app=neo4j`
- Verify password: `kubectl get secret -n swe neo4j-auth -o yaml`
- Check network policy allows connection

#### 2. Redis Connection Failed

```
Error: Connection refused to Redis
```

**Solution:**
- Check Redis is running: `kubectl get pods -n swe -l app=redis`
- Verify service: `kubectl get svc -n swe redis`

#### 3. NATS Connection Failed

```
Warning: NATS initialization failed
```

**Solution:**
- Service continues without NATS (degraded mode)
- Check NATS: `kubectl get pods -n swe -l app=nats`
- Set `ENABLE_NATS=false` to disable

#### 4. Context Build Fails

```
Error: Scope violation: missing scopes
```

**Solution:**
- Check scope policies in `config/prompt_scopes.yaml`
- Verify role and phase are valid
- Review logs for detailed scope information

## 🚀 Development

### Local Development

```bash
# Install dependencies
pip install -r services/context/requirements.txt

# Run with hot reload
watchmedo auto-restart \
  --directory=services/context \
  --pattern=*.py \
  --recursive \
  -- python services/context/server.py
```

### Generate gRPC Code

```bash
# Regenerate from proto
make context-proto

# Or manually
python -m grpc_tools.protoc \
  -I./specs \
  --python_out=./services/context/gen \
  --grpc_python_out=./services/context/gen \
  --pyi_out=./services/context/gen \
  ./specs/context.proto
```

### Update Proto

1. Edit `specs/context.proto`
2. Regenerate code: `make context-proto`
3. Update server implementation
4. Update tests
5. Update documentation

## 📚 Related Documentation

- [Context Architecture](../../docs/CONTEXT_ARCHITECTURE.md)
- [Scope Policies](../../config/prompt_scopes.yaml)
- [API Specification](../../specs/context.proto)
- [Deployment Guide](../../docs/DEPLOYMENT.md)

## 🤝 Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines.

## 📄 License

Apache License 2.0 - See [LICENSE](../../LICENSE)
