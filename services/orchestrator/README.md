# Orchestrator Service

**Architecture Pattern:** Hexagonal Architecture (Ports & Adapters)  
**Communication:** gRPC + NATS JetStream  
**Language:** Python 3.13

## 📋 Overview

The Orchestrator Service coordinates multi-agent deliberation and task execution in the SWE AI Fleet. It manages councils of AI agents, orchestrates deliberation rounds, and integrates with the Ray Executor for distributed agent execution.

This service has been refactored to follow **Hexagonal Architecture** principles, ensuring clean separation between domain logic, application use cases, and infrastructure concerns.

## 🏗️ Architecture

### Hexagonal Architecture Layers

```
services/orchestrator/
├── domain/                    # Pure business logic (no dependencies)
│   ├── entities/              # Domain entities with behavior
│   │   ├── agent_collection.py
│   │   ├── agent_config.py
│   │   ├── agent_type.py
│   │   ├── check_suite.py
│   │   ├── council_registry.py
│   │   ├── deliberation_result_data.py
│   │   ├── deliberation_status.py
│   │   ├── deliberation_submission.py
│   │   ├── role_collection.py
│   │   ├── service_configuration.py
│   │   └── statistics.py
│   ├── ports/                 # Interfaces (dependency inversion)
│   │   ├── agent_factory_port.py
│   │   ├── architect_port.py
│   │   ├── configuration_port.py
│   │   ├── council_factory_port.py
│   │   ├── council_query_port.py
│   │   ├── ray_executor_port.py
│   │   └── scoring_port.py
│   └── value_objects/         # Immutable data structures
│       ├── check_results.py
│       ├── deliberation.py
│       ├── metadata.py
│       └── task_constraints.py
├── application/               # Use cases (orchestration)
│   └── usecases/
│       ├── create_council_usecase.py
│       ├── deliberate_usecase.py
│       ├── delete_council_usecase.py
│       └── list_councils_usecase.py
├── infrastructure/            # External integrations
│   ├── adapters/              # Port implementations
│   │   ├── architect_adapter.py
│   │   ├── council_query_adapter.py
│   │   ├── deliberate_council_factory_adapter.py
│   │   ├── environment_configuration_adapter.py
│   │   ├── grpc_ray_executor_adapter.py
│   │   ├── scoring_adapter.py
│   │   └── vllm_agent_factory_adapter.py
│   ├── dto/                   # DTO abstraction layer
│   │   └── __init__.py        # Wraps orchestrator_pb2
│   ├── handlers/              # NATS event handlers
│   │   ├── agent_response_consumer.py
│   │   ├── context_consumer.py
│   │   ├── deliberation_collector.py
│   │   ├── nats_handler.py
│   │   └── planning_consumer.py
│   └── mappers/               # Domain ↔ DTO conversion
│       ├── check_suite_mapper.py
│       ├── council_info_mapper.py
│       ├── deliberate_response_mapper.py
│       ├── deliberation_result_data_mapper.py
│       ├── deliberation_status_mapper.py
│       ├── legacy_check_suite_mapper.py
│       ├── metadata_mapper.py
│       ├── orchestrate_response_mapper.py
│       ├── orchestrator_stats_mapper.py
│       ├── proposal_mapper.py
│       └── task_constraints_mapper.py
├── tests/                     # Comprehensive test suite
│   ├── domain/                # Domain logic tests (fast)
│   ├── application/           # Use case tests
│   └── infrastructure/        # Adapter & mapper tests
└── server.py                  # gRPC server with DI
```

### Key Design Principles

1. **Dependency Inversion (DIP):** Domain depends on abstractions (ports), not implementations
2. **Tell, Don't Ask:** Entities encapsulate behavior, not just data
3. **Fail-Fast:** Early validation with clear error messages
4. **Dependency Injection:** All dependencies injected via constructor
5. **Single Responsibility:** Each component has one reason to change

## 🔌 Ports (Interfaces)

| Port | Purpose | Adapter |
|------|---------|---------|
| `RayExecutorPort` | Submit deliberations to Ray | `GRPCRayExecutorAdapter` |
| `CouncilQueryPort` | Query council information | `CouncilQueryAdapter` |
| `AgentFactoryPort` | Create agent instances | `VLLMAgentFactoryAdapter` |
| `CouncilFactoryPort` | Create council instances | `DeliberateCouncilFactoryAdapter` |
| `ConfigurationPort` | Load service configuration | `EnvironmentConfigurationAdapter` |
| `ScoringPort` | Score and validate proposals | `ScoringAdapter` |
| `ArchitectPort` | Select architect agent | `ArchitectAdapter` |

## 🎯 Use Cases

### 1. CreateCouncilUseCase
Creates a new deliberation council with configured agents.

**Input:** Role, agent type, model config, number of agents  
**Output:** `CouncilCreationResult` (council, agents, duration)  
**Business Rules:**
- Agent type must be `VLLM` (no mocks in production)
- Model must be specified
- At least 1 agent required

### 2. DeliberateUseCase
Executes multi-agent deliberation on a task.

**Input:** Council, role, task description, constraints  
**Output:** `DeliberationResult` (proposals, metadata, duration, stats)  
**Business Rules:**
- Task description cannot be empty
- Records duration and updates statistics
- Delegates to council's `execute()` method

### 3. DeleteCouncilUseCase
Removes a council and returns its information.

**Input:** Role  
**Output:** `CouncilDeletionResult` (council, agents, role)  
**Business Rules:**
- Council must exist (fail-fast if not found)
- Returns both council and agents for logging/auditing

### 4. ListCouncilsUseCase
Lists all active councils with optional agent details.

**Input:** Council registry, include_agents flag  
**Output:** List of `CouncilInfo` objects  
**Business Rules:**
- Queries all registered councils
- Adapter enforces `include_agents=True` for consistency

## 🧪 Testing

### Test Organization

```bash
# Unit tests (fast, 112 tests)
make test-unit
bash scripts/test/unit.sh services/orchestrator/tests/

# Integration tests (with containers)
bash scripts/test/integration.sh

# E2E tests (full system)
bash scripts/test/e2e.sh

# Coverage report
bash scripts/test/coverage.sh
```

### Test Coverage

- **Domain:** 100% (entities, value objects)
- **Application:** 95% (use cases)
- **Infrastructure:** 90% (adapters, mappers)
- **Overall:** >90% (target: 90% minimum)

### Testing Philosophy

1. **Fast Unit Tests:** No I/O, pure logic, <0.3s per test
2. **Ports as Test Doubles:** Easy mocking via interfaces
3. **Tell, Don't Ask Tests:** Test behavior, not implementation
4. **Fail-Fast Validation:** Tests verify early error detection

## 🚀 Running the Service

### Local Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Generate protobuf files (temporary, not committed)
bash scripts/test/_generate_protos.sh

# Run tests
make test-unit

# Start service (requires NATS and Ray Executor)
python services/orchestrator/server.py
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_PORT` | `50060` | gRPC server port |
| `NATS_URL` | `nats://localhost:4222` | NATS JetStream URL |
| `RAY_EXECUTOR_ADDRESS` | `localhost:50070` | Ray Executor gRPC address |
| `VLLM_URL` | `http://localhost:8000` | vLLM inference URL |
| `VLLM_MODEL` | `Qwen/Qwen3-0.6B` | Default model name |

### Kubernetes Deployment

```bash
# Deploy to cluster (requires registry.underpassai.com)
kubectl apply -f deploy/k8s-integration/

# Check status
kubectl get pods -n swe-ai-fleet -l app=orchestrator

# View logs
kubectl logs -n swe-ai-fleet -l app=orchestrator -f
```

## 📊 Monitoring & Observability

### gRPC Endpoints

- `CreateCouncil` - Create new deliberation council
- `DeleteCouncil` - Remove existing council
- `ListCouncils` - List all active councils
- `Deliberate` - Execute multi-agent deliberation
- `Orchestrate` - Full orchestration (deliberation + architect selection)
- `GetDeliberationResult` - Query deliberation status
- `GetStatus` - Service health and statistics

### Statistics Tracked

- Total deliberations
- Deliberations per role
- Average duration
- Success/failure rates

## 🔄 Migration Notes

This service was refactored from a monolithic architecture to Hexagonal Architecture. Key changes:

1. **Before:** Direct gRPC DTO usage in business logic
2. **After:** Domain entities mapped via dedicated mappers

3. **Before:** `os.getenv()` scattered throughout code
4. **After:** `ConfigurationPort` with dependency injection

5. **Before:** Mocks allowed in production (`AgentType.MOCK`)
6. **After:** Production-only types, explicit validation

7. **Before:** Optional NATS (silent degradation)
8. **After:** Mandatory NATS (fail-fast on startup)

9. **Before:** No test coverage
10. **After:** 112 unit tests, >90% coverage

## 📚 Related Documentation

- [Microservices Architecture](../../docs/architecture/MICROSERVICES_ARCHITECTURE.md)
- [Component Interactions](../../docs/architecture/COMPONENT_INTERACTIONS.md)
- [Ray Executor Service](../ray_executor/README.md)
- [Context Service](../context/README.md)

## 🤝 Contributing

When adding new features:

1. **Domain First:** Create entities/VOs in `domain/`
2. **Port Definition:** Define interface in `domain/ports/`
3. **Use Case:** Implement orchestration in `application/usecases/`
4. **Adapter:** Implement port in `infrastructure/adapters/`
5. **Mapper:** Add DTO conversion in `infrastructure/mappers/`
6. **Tests:** Achieve >90% coverage
7. **Update Docs:** Keep this README current

## 📝 License

See [LICENSE](../../LICENSE) at repository root.
