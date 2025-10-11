# Estrategia de Testing para Consumers y Use Cases

## 🎯 Objetivo

Establecer una suite de tests completa para garantizar la calidad antes de implementar lógica adicional:
- **Unit Tests**: Casos de uso aislados
- **Integration Tests**: Consumers + NATS + Use Cases
- **E2E Tests**: Flujo completo entre servicios

---

## 📊 Pirámide de Tests

```
           /\
          /  \        E2E Tests (5%)
         /    \       - Flujo completo
        /------\      - Múltiples servicios
       /        \     - Infraestructura real
      /   Integration Tests (25%)
     /    - Consumers + NATS
    /     - Use cases + adapters
   /      - Redis/Neo4j testcontainers
  /--------------------------------\
  |        Unit Tests (70%)        |
  |  - Use cases mockados          |
  |  - Lógica de negocio           |
  |  - Domain entities             |
  \--------------------------------/
```

---

## 🧪 Unit Tests

### Context Service - Use Cases

#### 1. **ProjectDecisionUseCase**

```python
# tests/unit/context/usecases/test_project_decision.py

import pytest
from unittest.mock import Mock, call
from swe_ai_fleet.context.usecases.project_decision import ProjectDecisionUseCase


class TestProjectDecisionUseCase:
    """Unit tests for ProjectDecisionUseCase."""
    
    def test_execute_creates_decision_node(self):
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "TECHNICAL",
            "summary": "Use Redis for caching",
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        assert call_args[0][0] == "Decision"
        assert call_args[0][1] == "DEC-001"
        assert "kind" in call_args[0][2]
    
    def test_execute_creates_affects_relationship_when_sub_id_provided(self):
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "TECHNICAL",
            "summary": "Use Redis for caching",
            "sub_id": "TASK-001",  # ← Affects a subtask
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        assert mock_writer.upsert_entity.called
        assert mock_writer.relate.called
        
        relate_call = mock_writer.relate.call_args
        assert relate_call[0][0] == "DEC-001"  # src_id
        assert relate_call[0][1] == "AFFECTS"  # rel_type
        assert relate_call[0][2] == "TASK-001"  # dst_id
    
    def test_execute_no_relationship_when_no_sub_id(self):
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "TECHNICAL",
            "summary": "Use Redis for caching",
            # No sub_id
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        assert mock_writer.upsert_entity.called
        assert not mock_writer.relate.called
```

#### 2. **UpdateSubtaskStatusUseCase**

```python
# tests/unit/context/usecases/test_update_subtask_status.py

import pytest
from unittest.mock import Mock
from swe_ai_fleet.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase


class TestUpdateSubtaskStatusUseCase:
    """Unit tests for UpdateSubtaskStatusUseCase."""
    
    @pytest.mark.parametrize("status", [
        "QUEUED",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
    ])
    def test_execute_updates_subtask_status(self, status):
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {
            "sub_id": "TASK-001",
            "status": status,
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        assert call_args[0][0] == "Subtask"
        assert call_args[0][1] == "TASK-001"
        properties = call_args[0][2]
        assert properties["status"] == status
```

---

### Orchestrator Service - Use Cases

#### 3. **Deliberate UseCase**

```python
# tests/unit/orchestrator/usecases/test_deliberate.py

import pytest
from unittest.mock import Mock, MagicMock
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.domain.check_results.check_suite import CheckSuiteResult


class TestDeliberate:
    """Unit tests for Deliberate use case."""
    
    def test_execute_generates_proposals_from_all_agents(self):
        # Arrange
        mock_agents = [Mock() for _ in range(3)]
        for i, agent in enumerate(mock_agents):
            agent.generate.return_value = {"content": f"Proposal {i}"}
            agent.agent_id = f"agent-{i}"
        
        mock_scoring = Mock()
        mock_scoring.run_check_suite.return_value = CheckSuiteResult(
            lint=None, dryrun=None, policy=None
        )
        mock_scoring.score_checks.return_value = 0.8
        
        deliberate = Deliberate(
            agents=mock_agents,
            tooling=mock_scoring,
            rounds=1
        )
        
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        # Act
        results = deliberate.execute("Implement login", constraints)
        
        # Assert
        assert len(results) == 3
        for agent in mock_agents:
            agent.generate.assert_called_once()
    
    def test_execute_performs_peer_review_rounds(self):
        # Arrange
        mock_agents = [Mock() for _ in range(3)]
        for i, agent in enumerate(mock_agents):
            agent.generate.return_value = {"content": f"Initial proposal {i}"}
            agent.critique.return_value = f"Feedback for proposal"
            agent.revise.return_value = f"Revised proposal {i}"
            agent.agent_id = f"agent-{i}"
        
        mock_scoring = Mock()
        mock_scoring.run_check_suite.return_value = CheckSuiteResult(
            lint=None, dryrun=None, policy=None
        )
        mock_scoring.score_checks.return_value = 0.8
        
        deliberate = Deliberate(
            agents=mock_agents,
            tooling=mock_scoring,
            rounds=2  # ← 2 rounds
        )
        
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        # Act
        results = deliberate.execute("Implement login", constraints)
        
        # Assert
        # Each agent should critique and revise 2 times (2 rounds)
        for agent in mock_agents:
            assert agent.critique.call_count == 2
            assert agent.revise.call_count == 2
    
    def test_execute_returns_sorted_by_score_descending(self):
        # Arrange
        mock_agents = [Mock() for _ in range(3)]
        for i, agent in enumerate(mock_agents):
            agent.generate.return_value = {"content": f"Proposal {i}"}
            agent.agent_id = f"agent-{i}"
        
        mock_scoring = Mock()
        mock_scoring.run_check_suite.return_value = CheckSuiteResult(
            lint=None, dryrun=None, policy=None
        )
        # Different scores for each proposal
        mock_scoring.score_checks.side_effect = [0.7, 0.9, 0.6]
        
        deliberate = Deliberate(
            agents=mock_agents,
            tooling=mock_scoring,
            rounds=0  # No peer review for simplicity
        )
        
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        # Act
        results = deliberate.execute("Implement login", constraints)
        
        # Assert
        assert len(results) == 3
        assert results[0].score == 0.9  # Highest first
        assert results[1].score == 0.7
        assert results[2].score == 0.6  # Lowest last
```

#### 4. **Orchestrate UseCase**

```python
# tests/unit/orchestrator/usecases/test_orchestrate.py

import pytest
from unittest.mock import Mock, MagicMock
from swe_ai_fleet.orchestrator.usecases.orchestrate_usecase import Orchestrate
from swe_ai_fleet.orchestrator.domain.tasks.task import Task
from swe_ai_fleet.orchestrator.domain.agents.role import Role
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints


class TestOrchestrate:
    """Unit tests for Orchestrate use case."""
    
    def test_execute_delegates_to_appropriate_council(self):
        # Arrange
        mock_config = Mock()
        
        mock_dev_council = Mock()
        mock_dev_council.execute.return_value = [
            Mock(score=0.9),
            Mock(score=0.8),
        ]
        
        mock_qa_council = Mock()
        
        councils = {
            "DEV": mock_dev_council,
            "QA": mock_qa_council,
        }
        
        mock_architect = Mock()
        mock_architect.choose.return_value = {
            "winner": Mock(),
            "candidates": [],
        }
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Implement API endpoint", "TASK-001")
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        # Act
        result = orchestrate.execute(role, task, constraints)
        
        # Assert
        mock_dev_council.execute.assert_called_once_with(
            task.description, constraints
        )
        mock_qa_council.execute.assert_not_called()
    
    def test_execute_architect_selects_winner(self):
        # Arrange
        mock_config = Mock()
        
        ranked_results = [
            Mock(score=0.9),
            Mock(score=0.8),
            Mock(score=0.7),
        ]
        
        mock_council = Mock()
        mock_council.execute.return_value = ranked_results
        
        councils = {"DEV": mock_council}
        
        mock_architect = Mock()
        expected_result = {
            "winner": ranked_results[0],
            "candidates": ranked_results[1:],
        }
        mock_architect.choose.return_value = expected_result
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Implement API endpoint", "TASK-001")
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        # Act
        result = orchestrate.execute(role, task, constraints)
        
        # Assert
        mock_architect.choose.assert_called_once_with(
            ranked_results, constraints
        )
        assert result == expected_result
```

---

## 🔌 Integration Tests

### Context Service - Consumers

```python
# tests/integration/services/context/test_orchestration_consumer.py

import asyncio
import json
import pytest
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from services.context.consumers.orchestration_consumer import OrchestrationEventsConsumer
from swe_ai_fleet.context.adapters.neo4j_command_store import Neo4jCommandStore, Neo4jConfig


@pytest.mark.integration
class TestOrchestrationEventsConsumer:
    """Integration tests for OrchestrationEventsConsumer with real NATS."""
    
    @pytest.fixture
    async def nats_connection(self):
        """Connect to NATS server."""
        nc = await NATS().connect("nats://localhost:4222")
        js = nc.jetstream()
        yield nc, js
        await nc.close()
    
    @pytest.fixture
    def neo4j_store(self):
        """Neo4j command store for testing."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="testpassword"
        )
        store = Neo4jCommandStore(cfg=config)
        yield store
        # Cleanup
        store.execute_cypher("MATCH (n:Decision) WHERE n.node_id STARTS WITH 'TEST-' DELETE n")
    
    @pytest.mark.asyncio
    async def test_handles_deliberation_completed_event(
        self, nats_connection, neo4j_store
    ):
        # Arrange
        nc, js = nats_connection
        
        consumer = OrchestrationEventsConsumer(
            nc=nc,
            js=js,
            graph_command=neo4j_store,
            nats_publisher=None,
        )
        
        # Subscribe
        await consumer.start()
        
        # Publish test event
        event = {
            "story_id": "STORY-TEST-001",
            "task_id": "TASK-TEST-001",
            "decisions": [
                {
                    "id": "TEST-DEC-001",
                    "type": "TECHNICAL",
                    "rationale": "Test decision",
                }
            ],
            "timestamp": 1234567890,
        }
        
        await js.publish(
            "orchestration.deliberation.completed",
            json.dumps(event).encode()
        )
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Assert - verify decision was persisted to Neo4j
        result = neo4j_store.execute_cypher(
            "MATCH (d:Decision {node_id: 'TEST-DEC-001'}) RETURN d"
        )
        assert len(result) == 1
        assert result[0]["d"]["kind"] == "TECHNICAL"
```

---

## 🌍 E2E Tests

### Flujo Completo: Planning → Orchestrator → Context

```python
# tests/e2e/test_complete_flow.py

import asyncio
import json
import pytest
from nats.aio.client import Client as NATS


@pytest.mark.e2e
class TestCompleteOrchestratorFlow:
    """E2E tests for complete orchestration flow."""
    
    @pytest.fixture
    async def services_running(self):
        """Ensure all services are running via docker-compose."""
        # Assume docker-compose up is already done
        yield
    
    @pytest.fixture
    async def nats_connection(self):
        """Connect to NATS."""
        nc = await NATS().connect("nats://localhost:4222")
        js = nc.jetstream()
        yield nc, js
        await nc.close()
    
    @pytest.mark.asyncio
    async def test_plan_approved_triggers_orchestration(
        self, services_running, nats_connection
    ):
        # Arrange
        nc, js = nats_connection
        
        # Subscribe to orchestration events
        received_events = []
        
        async def collect_events(msg):
            data = json.loads(msg.data.decode())
            received_events.append(data)
            await msg.ack()
        
        await js.subscribe(
            "orchestration.task.dispatched",
            cb=collect_events,
            queue="test-queue"
        )
        
        # Act - Publish plan approved event
        plan_approved_event = {
            "story_id": "STORY-E2E-001",
            "plan_id": "PLAN-E2E-001",
            "roles": ["DEV", "QA"],
            "timestamp": 1234567890,
        }
        
        await js.publish(
            "planning.plan.approved",
            json.dumps(plan_approved_event).encode()
        )
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Assert
        assert len(received_events) > 0
        dispatched_event = received_events[0]
        assert dispatched_event["story_id"] == "STORY-E2E-001"
        assert "task_id" in dispatched_event
        assert "agent_id" in dispatched_event
    
    @pytest.mark.asyncio
    async def test_agent_completed_triggers_deliberation(
        self, services_running, nats_connection
    ):
        # Arrange
        nc, js = nats_connection
        
        # Subscribe to deliberation events
        received_events = []
        
        async def collect_events(msg):
            data = json.loads(msg.data.decode())
            received_events.append(data)
            await msg.ack()
        
        await js.subscribe(
            "orchestration.deliberation.completed",
            cb=collect_events,
            queue="test-queue"
        )
        
        # Act - Publish agent response
        agent_response = {
            "story_id": "STORY-E2E-002",
            "task_id": "TASK-E2E-002",
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "output": {"code": "...", "tests": "..."},
            "requires_deliberation": True,
            "task_description": "Implement login",
            "constraints": {
                "rubric": {"quality": "high"},
                "architect_rubric": {"k": 3}
            },
            "timestamp": 1234567890,
        }
        
        await js.publish(
            "agent.response.completed",
            json.dumps(agent_response).encode()
        )
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Assert
        assert len(received_events) > 0
        deliberation_event = received_events[0]
        assert deliberation_event["story_id"] == "STORY-E2E-002"
        assert deliberation_event["task_id"] == "TASK-E2E-002"
        assert "decisions" in deliberation_event
```

---

## 🏃 Comandos de Ejecución

### Unit Tests
```bash
# Context Service
pytest tests/unit/context/usecases/ -v

# Orchestrator Service
pytest tests/unit/orchestrator/usecases/ -v

# Todos los unit tests
pytest -m "not integration and not e2e" -v
```

### Integration Tests
```bash
# Context Service (requiere NATS + Neo4j)
podman-compose -f tests/integration/docker-compose.yml up -d
pytest tests/integration/services/context/ -m integration -v

# Orchestrator Service
pytest tests/integration/services/orchestrator/ -m integration -v
```

### E2E Tests
```bash
# Todos los servicios deben estar corriendo
podman-compose -f tests/e2e/docker-compose.e2e.yml up -d
pytest tests/e2e/ -m e2e -v --tb=short
```

---

## 📊 Coverage Goals

| Tipo | Target | Actual | Prioridad |
|------|--------|--------|-----------|
| Unit Tests | 90%+ | 0% | 🔴 Alta |
| Integration Tests | 70%+ | ~30% | 🟡 Media |
| E2E Tests | 50%+ | ~10% | 🟢 Baja |

---

## 🎯 Plan de Implementación

### Fase 1: Unit Tests (Alta Prioridad) ← **EMPEZAR AQUÍ**

1. ✅ Context Use Cases (2 horas)
   - ProjectDecisionUseCase
   - UpdateSubtaskStatusUseCase
   - ProjectSubtaskUseCase
   - ProjectCaseUseCase

2. ✅ Orchestrator Use Cases (3 horas)
   - Deliberate
   - Orchestrate
   - MockAgent (crear primero)

### Fase 2: Integration Tests (Media Prioridad)

3. ✅ Context Consumers (2 horas)
   - OrchestrationEventsConsumer
   - PlanningEventsConsumer

4. ✅ Orchestrator Consumers (2 horas)
   - OrchestratorPlanningConsumer
   - OrchestratorAgentResponseConsumer

### Fase 3: E2E Tests (Baja Prioridad)

5. ✅ Flujos completos (3 horas)
   - Plan approved → Task dispatched
   - Agent completed → Deliberation → Context updated

---

## 🔧 Herramientas y Configuración

### pytest.ini
```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require services)
    e2e: End-to-end tests (full system)
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

### conftest.py
```python
# tests/conftest.py
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require services)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full system)"
    )
```

---

## ✅ Próximo Paso Inmediato

**Crear y ejecutar Unit Tests** para validar la lógica antes de continuar:

1. Crear `tests/unit/context/usecases/test_project_decision.py`
2. Crear `tests/unit/context/usecases/test_update_subtask_status.py`
3. Crear `tests/unit/orchestrator/domain/agents/mock_agent.py` (implementation)
4. Crear `tests/unit/orchestrator/usecases/test_deliberate.py`
5. Crear `tests/unit/orchestrator/usecases/test_orchestrate.py`

**Tiempo estimado**: 4-5 horas para suite completa de unit tests

¿Empezamos con los unit tests del Context Service?

