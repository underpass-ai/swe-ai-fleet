# E2E Tests - Refactored Architecture

## Overview

This directory contains the refactored e2e tests that run as Kubernetes Jobs.

The tests validate the complete SWE AI Fleet system with real services deployed in Kubernetes.

## Architecture

### Hexagonal Architecture (Ports & Adapters)

```
tests/e2e/refactored/
├── ports/                    # Interfaces (abstractions)
│   ├── context_service_port.py
│   ├── orchestrator_service_port.py
│   ├── neo4j_validator_port.py
│   └── valkey_validator_port.py
├── adapters/                 # Implementations
│   ├── grpc_context_adapter.py
│   ├── grpc_orchestrator_adapter.py
│   ├── neo4j_validator_adapter.py
│   └── valkey_validator_adapter.py
├── dto/                      # Data Transfer Objects
│   ├── story_dto.py
│   └── council_dto.py
├── test_001_story_persistence.py
└── test_002_multi_agent_planning.py
```

### Test Suite

#### Test 001: Story Persistence
- **Purpose**: Validate PO can create user story and it persists correctly
- **Flow**:
  1. PO creates medium-complexity user story via Context Service (gRPC)
  2. Story persisted in Neo4j as `ProjectCase` node
  3. Story cached in Valkey for fast access
  4. Validate all properties in both stores
  5. Test phase transitions

#### Test 002: Multi-Agent Planning
- **Purpose**: Validate multi-agent deliberation and task generation
- **Flow**:
  1. Create user story (prerequisite)
  2. Transition story to BUILD phase
  3. Create councils: 3 DEVs, 1 ARCHITECT, 1 QA
  4. Each council deliberates on the story
  5. Generate decisions and store in Neo4j
  6. Validate graph structure and relationships
  7. Validate Valkey caching

## Running Tests

### Local Development

```bash
# Build the test runner image
cd jobs/e2e-tests
make build

# Run tests locally (requires services running)
make run-local
```

### Kubernetes Job

```bash
# Build and push image
make build-push

# Deploy job to Kubernetes
kubectl apply -f job.yaml

# Watch job progress
kubectl get jobs -n swe-ai-fleet -w

# View logs
kubectl logs -n swe-ai-fleet job/e2e-tests -f

# Check results
kubectl get pods -n swe-ai-fleet -l app=e2e-tests
```

### Manual Job Trigger

```bash
# Delete old job (if exists)
kubectl delete job e2e-tests -n swe-ai-fleet

# Create new job
kubectl create -f job.yaml

# Follow logs
kubectl logs -n swe-ai-fleet -l app=e2e-tests -f
```

## Environment Variables

Required environment variables (set in `job.yaml`):

| Variable | Description | Example |
|----------|-------------|---------|
| `CONTEXT_SERVICE_URL` | Context Service gRPC endpoint | `context-service:50054` |
| `ORCHESTRATOR_SERVICE_URL` | Orchestrator Service gRPC endpoint | `orchestrator-service:50055` |
| `NEO4J_URI` | Neo4j Bolt connection URI | `bolt://neo4j:7687` |
| `NEO4J_USERNAME` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | From secret |
| `VALKEY_HOST` | Valkey (Redis) host | `valkey` |
| `VALKEY_PORT` | Valkey port | `6379` |

## Test Isolation

All tests include cleanup:
- Neo4j: `DETACH DELETE` all test story data
- Valkey: Delete all keys matching test pattern
- Councils: Delete all created councils

## Troubleshooting

### Job Failed

```bash
# Check job status
kubectl describe job e2e-tests -n swe-ai-fleet

# Check pod logs
kubectl logs -n swe-ai-fleet -l app=e2e-tests

# Check pod events
kubectl describe pod -n swe-ai-fleet -l app=e2e-tests
```

### Service Connection Issues

```bash
# Verify services are running
kubectl get svc -n swe-ai-fleet

# Check Context Service
kubectl logs -n swe-ai-fleet -l app=context-service --tail=50

# Check Orchestrator Service
kubectl logs -n swe-ai-fleet -l app=orchestrator-service --tail=50

# Verify Neo4j
kubectl exec -it -n swe-ai-fleet statefulset/neo4j -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n);"

# Verify Valkey
kubectl exec -it -n swe-ai-fleet statefulset/valkey -- redis-cli ping
```

### Image Pull Errors

```bash
# Verify image exists in registry
podman search registry.underpassai.com/swe-ai-fleet/e2e-tests

# Pull image manually
podman pull registry.underpassai.com/swe-ai-fleet/e2e-tests:v1.0.0
```

## Design Principles

1. **Hexagonal Architecture**: Clear separation between business logic (tests) and infrastructure (adapters)
2. **Fail-Fast**: All DTOs validate on construction
3. **Test Isolation**: Each test cleans up its data
4. **No Mocks**: Tests use real services in Kubernetes
5. **Strong Typing**: All functions have type hints
6. **Explicit Dependencies**: Ports injected via pytest fixtures

## Future Enhancements

- [ ] Add Test 003: Task execution with workspace validation
- [ ] Add Test 004: End-to-end story lifecycle
- [ ] Integrate with CI/CD pipeline
- [ ] Add performance benchmarks
- [ ] Generate test reports (JUnit XML, HTML)
- [ ] Add distributed tracing for debugging

