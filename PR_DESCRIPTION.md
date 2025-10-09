# Context Service Microservice

## 🎯 Overview

Converts the Python `context` bounded context into a production-ready microservice with gRPC and NATS support.

## 📦 What's New

### gRPC API (Synchronous)
- **GetContext**: Retrieve hydrated, role-specific context for agents
- **UpdateContext**: Record context changes from agent execution
- **RehydrateSession**: Rebuild complete session context from persistent storage
- **ValidateScope**: Check if provided scopes are allowed for role/phase

### NATS Messaging (Asynchronous)
- Event subscriptions: `context.update.request`, `context.rehydrate.request`
- Event publications: `context.update.response`, `context.rehydrate.response`, `context.events.updated`
- JetStream integration with durable consumers
- Graceful degradation if NATS is unavailable

### Infrastructure
- **Docker**: Containerized with health checks (liveness/readiness probes)
- **Kubernetes**: Deployment with 2 replicas, ConfigMap, resource limits
- **Deployment Script**: Automated build, push, and deploy
- **Makefile**: 12 commands for build, deploy, test, logs, etc.

## 🏗️ Architecture

```
External Clients (Orchestrator, Agents)
           ↓
       gRPC (sync)
           ↓
   Context Service (Python)
   ├── gRPC Server (port 50054)
   │   ├── GetContext
   │   ├── UpdateContext
   │   ├── RehydrateSession
   │   └── ValidateScope
   ├── NATS Handler (async)
   │   ├── context.update.request
   │   ├── context.rehydrate.request
   │   └── context.events.updated
   └── Domain Layer (DDD)
       ├── SessionRehydrationUseCase
       ├── ContextAssembler
       └── PromptScopePolicy
           ↓
   Neo4j (graph) + Redis (cache)
```

## 📊 Changes

### Files Added/Modified (16 files)

| File | Lines | Description |
|------|-------|-------------|
| `specs/context.proto` | 190 | Protocol Buffer definition |
| `services/context/server.py` | 467 | gRPC server with NATS integration |
| `services/context/nats_handler.py` | 172 | NATS event handler |
| `services/context/gen/*.py` | 592 | Generated gRPC code |
| `services/context/requirements.txt` | 15 | Python dependencies |
| `services/context/Dockerfile` | 33 | Container image |
| `services/context/README.md` | 438 | Complete documentation |
| `deploy/k8s/context-service.yaml` | 100 | Kubernetes deployment |
| `scripts/infra/deploy-context.sh` | 60 | Deployment script |
| `Makefile.context` | 80 | Build/deploy commands |
| `tests/unit/services/context/test_server.py` | 624 | Unit tests (19 tests) |
| `tests/integration/test_context_service_integration.py` | 480 | Integration tests (11 tests) |
| `tests/conftest.py` | 26 | Pytest configuration |
| `pyproject.toml` | +1 | Exclude protobuf generated files from linting |

**Total: ~2,600 lines of code**

## ✅ Testing

### Test Results
```
✅ 30 tests passing (19 unit + 11 integration)
✅ 4 tests skipped (E2E requiring real services)
✅ 0 linter errors (Ruff)
✅ All existing tests still passing
```

### Test Coverage
- ✅ All gRPC methods (GetContext, UpdateContext, RehydrateSession, ValidateScope)
- ✅ NATS event handling (publish, subscribe, error handling)
- ✅ Error scenarios and edge cases
- ✅ Helper methods and utilities
- ✅ Resilience tests (Neo4j/Redis failures)

### Running Tests
```bash
# Unit tests
pytest tests/unit/services/context/ -v

# Integration tests
pytest tests/integration/test_context_service_integration.py -v -m "not e2e"

# All tests
pytest tests/unit/services/context/ tests/integration/test_context_service_integration.py -v
```

## 🚀 Deployment

### Build and Deploy
```bash
# Build image
make context-build

# Deploy to Kubernetes
./scripts/infra/deploy-context.sh

# Check status
kubectl get pods -n swe -l app=context
kubectl logs -n swe -l app=context -f
```

### Test the Service
```bash
# Port forward
kubectl port-forward -n swe svc/context 50054:50054

# Test with grpcurl
grpcurl -plaintext -d '{
  "story_id": "USR-001",
  "role": "DEV",
  "phase": "BUILD"
}' localhost:50054 fleet.context.v1.ContextService/GetContext
```

## 🔧 Configuration

### Environment Variables
- `GRPC_PORT`: gRPC server port (default: 50054)
- `NEO4J_URI`: Neo4j connection URI (required)
- `NEO4J_PASSWORD`: Neo4j password from secret (required)
- `REDIS_HOST`: Redis hostname (required)
- `NATS_URL`: NATS server URL (optional)
- `ENABLE_NATS`: Enable NATS messaging (default: true)

### Kubernetes Resources
- **Replicas**: 2
- **CPU**: 250m (request) - 1000m (limit)
- **Memory**: 512Mi (request) - 1Gi (limit)

## 📚 Documentation

- **API Reference**: `services/context/README.md`
- **Protocol Buffer**: `specs/context.proto`
- **Deployment Guide**: `scripts/infra/deploy-context.sh`
- **Architecture**: `CONTEXT_SERVICE_SUMMARY.md`

## 🔗 Integration Points

### Current
- ✅ Neo4j (decision graph, long-term storage)
- ✅ Redis (planning data, short-term cache)
- ✅ NATS (async event messaging)
- ✅ Python context domain logic

### Future
- Orchestrator (request context for agent execution)
- Planning Service (sync story state changes)
- Workspace Service (record execution results)
- Gateway (REST API wrapper)

## 🎯 Related

- **Milestone**: M2 (Context and Minimization)
- **Issue**: Closes #<issue-number>
- **RFC**: RFC-0003 (Collaboration Flow)

## ✅ Checklist

- [x] Code implemented and tested
- [x] All tests passing (30/30)
- [x] Linter passing (0 errors)
- [x] Documentation complete
- [x] Dockerfile and K8s manifests
- [x] Deployment script tested
- [x] No breaking changes to existing code
- [ ] Code review
- [ ] Integration testing with real services
- [ ] Performance benchmarking

## 🚨 Notes

- Generated protobuf files (`*_pb2.py`) excluded from linting
- NATS is optional - service works without it (degraded mode)
- E2E tests marked as skip (require running Neo4j/Redis/NATS)
- Node_modules committed (from ui/po-react) - consider adding to .gitignore

## 📸 Screenshots

### Test Results
```
30 passed, 4 skipped, 5 deselected, 3 warnings in 0.62s
```

### Ruff Check
```
All checks passed!
```

---

## 🔐 Security Review (SonarCloud)

All security hotspots have been reviewed and addressed:

### ✅ Resolved Issues

1. **Hard-coded Password in Tests** (HIGH)
   - **Status**: Safe - Test credential for mocked backend
   - **Fix**: Added `# nosec` comment
   - **Location**: `tests/unit/services/context/test_server.py:86`

2. **Root User in Docker** (MEDIUM)
   - **Status**: Fixed
   - **Fix**: Container now runs as non-root user `appuser:1000`
   - **Location**: `services/context/Dockerfile:25-29`

3. **Service Account Token Mounting** (MEDIUM)
   - **Status**: Fixed
   - **Fix**: Disabled with `automountServiceAccountToken: false`
   - **Location**: `deploy/k8s/context-service.yaml:39`

4. **Storage Requests** (MEDIUM)
   - **Status**: Fixed
   - **Fix**: Added ephemeral-storage requests (1Gi) and limits (2Gi)
   - **Location**: `deploy/k8s/context-service.yaml:74,78`

5. **Async Task Garbage Collection** (MAJOR BUG)
   - **Status**: Fixed
   - **Fix**: Store task reference and add error callback
   - **Location**: `services/context/server.py:164-174`

### ℹ️ Acknowledged Issues

- **Insecure gRPC Channel**: Acceptable for internal cluster communication. TLS will be added in future PR for production hardening.
- **Generated Code Issues** (`*_pb2_grpc.py`): Cannot be modified, generated by protoc.
- **Node Modules Issues**: External dependencies, not part of our codebase.

---

**Ready for review and merge** ✅

