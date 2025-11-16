# 🧪 Testing Strategy & Architecture

> **Documento Normativo**: Complete reference for testing across SWE AI Fleet
> Combines Testing Strategy (examples) + Testing Architecture (principles) into single source of truth

---

## 📐 Principios Arquitectónicos de Testing

### 1. Testing Pyramid

```
                    ╔═══════════════════╗
                    ║   E2E Tests       ║  ~10% (12 tests)
                    ║   Full System     ║  Cluster K8s
                    ╚═══════════════════╝  ~3-5 min
                  ╔═════════════════════════╗
                  ║  Integration Tests      ║  ~20% (45 tests)
                  ║  Component Boundaries   ║  Containers
                  ╚═════════════════════════╝  ~30-60s
            ╔═════════════════════════════════════╗
            ║         Unit Tests                  ║  ~70% (596 tests)
            ║  Domain Logic + Adapters            ║  Mocks
            ╚═════════════════════════════════════╝  ~3s
```

**Ratio Ideal**: 70% unit / 20% integration / 10% E2E
**Coverage Mínimo**: 90% en nuevo código (SonarQube quality gate)

### 2. Separation of Concerns en Tests

```
tests/
├── unit/                    ← Domain + Application + Adapters (isolated)
│   ├── orchestrator/        ← Pure business logic
│   ├── context/            ← Domain entities & use cases
│   ├── agents/             ← Agent implementations
│   └── tools/              ← Tool implementations
│
├── integration/             ← Port implementations (real infra)
│   ├── services/orchestrator/  ← gRPC + NATS + Ray
│   ├── services/context/       ← gRPC + Neo4j + Valkey
│   └── archived/              ← Legacy tests (reference)
│
└── e2e/                     ← Full system (deployed K8s)
    ├── test_system_e2e.py      ← Complete workflows
    ├── test_orchestrator_cluster.py  ← Deliberation E2E
    └── test_ray_vllm_e2e.py    ← GPU execution E2E
```

### 3. Hexagonal Architecture + Testing

```
┌─────────────────────────────────────────────────────┐
│        TESTS (Verification Layer)                   │
├─────────────────────────────────────────────────────┤
│  Unit: Mock all Ports          Integration: Real   │
│  Domain logic isolated         Infrastructure      │
│  Fast (<300ms each)            Slower (30s-60s)    │
└─────────────────────────────────────────────────────┘
                    ↓ Verify
┌─────────────────────────────────────────────────────┐
│  Domain Layer    Application Layer   Infrastructure │
│  ────────────────────────────────────────────────── │
│  Entities        Use Cases          Adapters       │
│  Value Objects   Ports (interfaces) Consumers      │
│  Events          DTOs               Handlers       │
│  ────────────────────────────────────────────────── │
│  NO external     NO concretions     All external   │
│  deps            Dependencies via   dependencies   │
│                  Constructor        implemented    │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Objetivo

Establecer una suite de tests completa para garantizar la calidad antes de implementar lógica adicional:
- **Unit Tests**: Casos de uso aislados
- **Integration Tests**: Consumers + NATS + Use Cases
- **E2E Tests**: Flujo completo entre servicios

**Ejecutar**:
```bash
make test-unit           # Fast unit tests (~3s)
make test-integration    # Integration tests (~45s)
make test-e2e           # Full system tests (~3-5 min)
make test-all           # Complete test suite
```

---

## 🧪 Unit Tests

### Context Service - Use Cases

#### 1. **ProjectDecisionUseCase**

```python
# tests/unit/context/usecases/test_project_decision.py

import pytest
from unittest.mock import Mock
from core.context.usecases.project_decision import ProjectDecisionUseCase
from core.context.domain.decision import Decision
from core.context.domain.entities import Agent, Project

def test_project_decision_success():
    """Test project decision use case success path."""
    # Arrange
    mock_storage = Mock()
    use_case = ProjectDecisionUseCase(storage=mock_storage)

    project = Project(id="proj-123", name="Feature X", status="ACTIVE")
    agent = Agent(id="agent-001", role="ARCHITECT", model="Qwen")
    decision_text = "Implement using hexagonal architecture"

    # Act
    decision = use_case.execute(
        project=project,
        agent=agent,
        decision_text=decision_text
    )

    # Assert
    assert decision.project_id == "proj-123"
    assert decision.agent_id == "agent-001"
    assert decision.text == decision_text
    mock_storage.save_decision.assert_called_once()
```

#### 2. **ContextAssemblyUseCase**

```python
def test_context_assembly_selects_relevant_nodes():
    """Test that context assembly picks only relevant nodes."""
    # Arrange
    mock_graph = Mock()
    mock_graph.query_related_nodes.return_value = [
        {"id": "node-1", "relevance": 0.95},
        {"id": "node-2", "relevance": 0.50},  # Below threshold
        {"id": "node-3", "relevance": 0.98},
    ]

    use_case = ContextAssemblyUseCase(graph_port=mock_graph)

    # Act
    context = use_case.assemble_for_task(
        task_id="task-123",
        role="DEVELOPER",
        threshold=0.75  # Only nodes > 75% relevant
    )

    # Assert
    assert len(context.nodes) == 2  # Only node-1 and node-3
    assert "node-2" not in [n["id"] for n in context.nodes]
    assert len(context.tokens) < 300  # Surgical precision
```

---

## 🧩 Integration Tests

### NATS + Use Cases

```python
# tests/integration/context/test_planning_consumer.py

import pytest
import asyncio
from nats.aio.client import Client as NATS
from testcontainers.nats import NatsContainer
from services.context.consumers.planning_events_consumer import PlanningEventsConsumer

@pytest.mark.asyncio
async def test_planning_consumer_processes_story_created_event():
    """Integration: NATS consumer processes real events."""
    # Arrange
    async with NatsContainer() as nats_container:
        nats_url = nats_container.get_connection_url()
        nc = NATS()
        await nc.connect(nats_url)
        js = nc.jetstream()

        # Create stream
        await js.add_stream(
            name="PLANNING_EVENTS",
            subjects=["planning.story.created"]
        )

        # Create consumer
        consumer = PlanningEventsConsumer(nats_client=nc)

        # Act: Publish event
        await js.publish("planning.story.created", json.dumps({
            "story_id": "story-123",
            "title": "Implement auth",
            "project_id": "proj-456"
        }).encode())

        # Start consumer in background
        task = asyncio.create_task(consumer.start())
        await asyncio.sleep(0.5)  # Let consumer process

        # Assert
        assert consumer.messages_processed == 1
        task.cancel()
        await nc.close()
```

---

## 📊 Coverage Targets

| Component | Type | Coverage | Target | Status |
|-----------|------|----------|--------|--------|
| **Domain Layer** | unit | 95% | ≥90% | ✅ Pass |
| **Use Cases** | unit | 92% | ≥90% | ✅ Pass |
| **Adapters** | integration | 88% | ≥85% | ✅ Pass |
| **Consumers** | integration | 85% | ≥85% | ✅ Pass |
| **E2E Flows** | e2e | 100% | ≥80% | ✅ Pass |
| **Overall** | all | 90% | ≥90% | ✅ Pass |

---

## ✅ Best Practices

### 1. Mock External Dependencies in Unit Tests

```python
# ✅ GOOD: Mock the port (interface)
mock_storage = Mock(spec=StoragePort)
use_case = MyUseCase(storage_port=mock_storage)

# ❌ BAD: Try to mock concrete implementation
mock_neo4j = Mock()  # Too low-level
```

### 2. Test Behavior, Not Implementation

```python
# ✅ GOOD: Assert outcomes
assert decision.status == "APPROVED"
assert decision.created_at is not None

# ❌ BAD: Assert implementation details
assert len(decision.__dict__) == 5
mock_storage.save.assert_called_with_args(...)  # Too specific
```

### 3. Use Fixtures for Reusable Objects

```python
# ✅ GOOD: Reusable fixtures
@pytest.fixture
def sample_project():
    return Project(id="proj-123", name="Feature X")

# ❌ BAD: Create objects inline everywhere
project = Project(id="proj-123", name="Feature X")  # Repeated
```

### 4. Test Edge Cases First

```python
# ✅ GOOD: Cover edge cases
@pytest.mark.parametrize("invalid_input", ["", None, -1])
def test_rejects_invalid_input(invalid_input):
    with pytest.raises(ValueError):
        use_case.execute(invalid_input)
```

---

## 🔄 CI/CD Integration

### GitHub Actions (Example)

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: make test-unit

      - name: Run integration tests
        run: make test-integration

      - name: Upload coverage
        run: |
          pip install coverage
          coverage report --fail-under=90
```

---

## 📖 Related Documentation

- [HEXAGONAL_ARCHITECTURE_PRINCIPLES.md](../HEXAGONAL_ARCHITECTURE_PRINCIPLES.md) - Architecture enforcement
- [README.md](../../services/*/README.md) - Service-specific test guides
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Testing expectations

---

**Status**: ✅ **CANONICAL REFERENCE**
**Coverage**: Unit + Integration + E2E
**Last Updated**: 2025-11-15


