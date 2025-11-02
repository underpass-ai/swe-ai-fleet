# E2E Tests - Refactored (Hexagonal Architecture)

## Overview

Refactored end-to-end tests following **Hexagonal Architecture** (Ports & Adapters) principles, designed to run as **Kubernetes Jobs** against real services deployed in the cluster.

## Key Features

- ✅ **Hexagonal Architecture**: Clean separation between test logic and infrastructure
- ✅ **Ports & Adapters**: Easy to mock for unit tests, real implementations for e2e
- ✅ **Immutable DTOs**: Fail-fast validation with `@dataclass(frozen=True)`
- ✅ **Strong Typing**: Full type hints on all functions
- ✅ **Data Preservation**: Cleanup disabled - data preserved for inspection (use helper scripts)
- ✅ **No Mocks**: Tests use real services in Kubernetes
- ✅ **Multi-stage Build**: Protobuf generation inside container

## Architecture

```
tests/e2e/refactored/
├── ports/                          # Interfaces (abstractions)
│   ├── context_service_port.py     # Context Service operations
│   ├── orchestrator_service_port.py # Orchestrator operations
│   ├── neo4j_validator_port.py     # Neo4j graph validation
│   └── valkey_validator_port.py    # Valkey (Redis) validation
├── adapters/                       # Concrete implementations
│   ├── grpc_context_adapter.py     # gRPC client for Context Service
│   ├── grpc_orchestrator_adapter.py # gRPC client for Orchestrator
│   ├── neo4j_validator_adapter.py  # Neo4j driver integration
│   └── valkey_validator_adapter.py # Redis client integration
├── dto/                            # Data Transfer Objects
│   ├── story_dto.py                # Story-related DTOs
│   └── council_dto.py              # Council-related DTOs
├── fixtures/                       # Shared test data
├── validators/                     # Custom validators
├── conftest.py                     # Pytest fixtures
├── test_001_story_persistence.py  # Test 001
├── test_002_multi_agent_planning.py # Test 002
├── ARCHITECTURE.md                 # Detailed architecture docs
└── README.md                       # This file
```

## Test Cases

### Test 001: Story Persistence

**Purpose**: Validate that the PO can create a user story and it persists correctly in both Neo4j and Valkey.

**Flow**:
1. PO creates a medium-complexity user story via Context Service (gRPC)
2. Story is persisted in Neo4j as a `ProjectCase` node
3. Story is cached in Valkey for fast access
4. Validate all properties in both stores
5. Test phase transitions (DESIGN → BUILD)

**Validations**:
- ✅ ProjectCase node exists in Neo4j with correct properties
- ✅ Story hash exists in Valkey with all required fields
- ✅ Phase transitions are recorded correctly
- ✅ Invalid phase values are rejected at DTO validation

**Test variants**:
- `test_001_po_creates_story_validates_persistence` - Happy path
- `test_001b_story_creation_validates_phase_transition` - Phase transitions
- `test_001c_story_creation_fails_with_invalid_phase` - Validation errors

---

### Test 002: Multi-Agent Planning

**Purpose**: Validate the complete multi-agent deliberation flow with decision and task generation.

**Flow**:
1. Create user story (prerequisite)
2. Transition story to BUILD phase
3. Create agent councils:
   - 3 DEV agents
   - 1 ARCHITECT agent
   - 1 QA agent
4. Each council deliberates on the story from their perspective
5. Generate decisions for each role
6. Store decisions in Neo4j with MADE_DECISION relationships
7. Validate graph structure and Valkey caching

**Validations**:
- ✅ Councils created with correct number of agents
- ✅ Deliberation produces multiple ranked proposals
- ✅ Winner is selected (rank 1 proposal)
- ✅ Decisions stored in Neo4j (one per role: DEV, ARCHITECT, QA)
- ✅ MADE_DECISION relationships exist
- ✅ Decision metadata (role, winner_id) is correct
- ✅ Story context in Valkey reflects BUILD phase

**Test variants**:
- `test_002_multi_agent_planning_full_flow` - Complete flow
- `test_002b_deliberation_produces_ranked_proposals` - Ranking validation

---

## Running Tests

### Local Development

```bash
# Build test runner image
cd jobs/e2e-tests
make build

# Run tests locally (requires services running)
make run-local
```

### Kubernetes Job

```bash
# Build and push to registry
cd jobs/e2e-tests
make build-push

# Deploy job to Kubernetes
kubectl apply -f job.yaml

# Watch job progress
kubectl get jobs -n swe-ai-fleet -w

# View logs in real-time
kubectl logs -n swe-ai-fleet job/e2e-tests -f

# Check job status
kubectl describe job e2e-tests -n swe-ai-fleet
```

### Manual Execution

```bash
# Delete old job (if exists)
kubectl delete job e2e-tests -n swe-ai-fleet

# Create new job
kubectl create -f jobs/e2e-tests/job.yaml

# Follow logs
kubectl logs -n swe-ai-fleet -l app=e2e-tests -f
```

## Environment Variables

Required for test execution (configured in `job.yaml`):

| Variable | Description | Example |
|----------|-------------|---------|
| `CONTEXT_SERVICE_URL` | Context Service gRPC endpoint | `context-service:50054` |
| `ORCHESTRATOR_SERVICE_URL` | Orchestrator Service gRPC endpoint | `orchestrator-service:50055` |
| `NEO4J_URI` | Neo4j Bolt connection URI | `bolt://neo4j:7687` |
| `NEO4J_USERNAME` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | From K8s secret |
| `VALKEY_HOST` | Valkey (Redis) host | `valkey` |
| `VALKEY_PORT` | Valkey port | `6379` |

## Ports (Interfaces)

### ContextServicePort
- `initialize_project_context()` - Create new story
- `add_project_decision()` - Add decision to story
- `transition_phase()` - Transition story phase

### OrchestratorServicePort
- `create_council()` - Create agent council for a role
- `deliberate()` - Execute multi-agent deliberation
- `delete_council()` - Delete council and agents

### Neo4jValidatorPort
- `validate_story_node_exists()` - Validate ProjectCase node
- `validate_decision_nodes_exist()` - Validate decision nodes
- `validate_task_nodes_exist()` - Validate task nodes
- `validate_relationships_exist()` - Validate graph relationships
- `cleanup_story_data()` - Clean up test data

### ValkeyValidatorPort
- `validate_key_exists()` - Validate Redis key exists
- `validate_hash_field()` - Validate hash field value
- `validate_task_context_exists()` - Validate task context
- `cleanup_keys()` - Clean up test keys

## Design Principles

1. **Hexagonal Architecture**: Clear separation between business logic (tests) and infrastructure (adapters)
2. **Fail-Fast**: All DTOs validate on construction, raise `ValueError` if invalid
3. **Test Isolation**: Each test cleans up its data (Neo4j + Valkey)
4. **No Mocks in E2E**: Tests use real services deployed in Kubernetes
5. **Strong Typing**: All functions have complete type hints
6. **Dependency Injection**: Ports injected via pytest fixtures
7. **Immutability**: DTOs are frozen dataclasses
8. **No Reflection**: Zero use of `setattr`, `__dict__`, etc.

## Compliance with Project Rules

✅ **All code, docstrings, comments in English**
✅ **Hexagonal Architecture (Ports & Adapters)**
✅ **Immutable DTOs with `@dataclass(frozen=True)`**
✅ **Fail-fast validation in `__post_init__`**
✅ **NO reflection or dynamic mutation**
✅ **NO `to_dict()` / `from_dict()` in DTOs**
✅ **Strong typing with complete type hints**
✅ **Dependency injection via ports**
✅ **Tests included with edge cases**

## Troubleshooting

### Job Failed

```bash
# Check job status
kubectl describe job e2e-tests -n swe-ai-fleet

# Check pod logs
kubectl logs -n swe-ai-fleet -l app=e2e-tests --tail=100

# Check pod events
kubectl get events -n swe-ai-fleet --sort-by='.lastTimestamp'
```

### Service Connection Issues

```bash
# Verify services are running
kubectl get svc -n swe-ai-fleet
kubectl get pods -n swe-ai-fleet

# Test Context Service
kubectl logs -n swe-ai-fleet -l app=context-service --tail=50

# Test Orchestrator Service
kubectl logs -n swe-ai-fleet -l app=orchestrator-service --tail=50

# Test Neo4j connection
kubectl exec -it -n swe-ai-fleet statefulset/neo4j -- cypher-shell -u neo4j

# Test Valkey connection
kubectl exec -it -n swe-ai-fleet statefulset/valkey -- redis-cli ping
```

### Image Pull Errors

```bash
# Verify image exists
podman images | grep e2e-tests

# Pull manually
podman pull registry.underpassai.com/swe-ai-fleet/e2e-tests:v1.0.0

# Check registry
curl -k https://registry.underpassai.com/v2/_catalog
```

## Future Enhancements

- [ ] Test 003: Task execution with workspace validation
- [ ] Test 004: Complete story lifecycle (DESIGN → BUILD → TEST → VALIDATE)
- [ ] CI/CD integration (GitHub Actions, GitLab CI)
- [ ] Performance benchmarks (latency, throughput)
- [ ] Test reports (JUnit XML, HTML coverage)
- [ ] Distributed tracing for debugging
- [ ] Retry logic in adapters for transient failures
- [ ] Structured logging with correlation IDs

## Helper Scripts

### View Test Data
```bash
cd tests/e2e/refactored
./view-test-data.sh
```

Shows:
- Neo4j node types and counts
- ProjectCase nodes (stories)
- PhaseTransition nodes  
- Valkey keys (story:*, swe:case:*, context:*)
- Database statistics

### Clear Test Data
```bash
cd tests/e2e/refactored
./clear-test-data.sh
```

Clears:
- All Neo4j nodes and relationships
- All Valkey keys
- Provides before/after verification

### Manual Data Inspection

**Neo4j - View specific story:**
```bash
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (p:ProjectCase {story_id: 'STORY_ID'}) RETURN p"
```

**Valkey - View specific story hash:**
```bash
kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli HGETALL story:STORY_ID
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Detailed architecture documentation
- **[RESOLVED_ISSUES.md](RESOLVED_ISSUES.md)**: Documented fixes and resolutions  
- **[jobs/e2e-tests/README.md](../../jobs/e2e-tests/README.md)**: Job runner documentation
- **[jobs/e2e-tests/Dockerfile](../../jobs/e2e-tests/Dockerfile)**: Multi-stage build details

## Contact

**Author**: Tirso García Ibáñez (Software Architect)
**Project**: SWE AI Fleet
**License**: MIT

