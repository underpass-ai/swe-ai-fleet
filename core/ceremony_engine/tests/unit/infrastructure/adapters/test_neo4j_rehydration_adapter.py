"""Unit tests for Neo4jRehydrationAdapter."""

import pytest
from dataclasses import replace
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    Inputs,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.ceremony_engine.infrastructure.adapters.neo4j_rehydration_adapter import (
    Neo4jRehydrationAdapter,
)


def create_test_definition() -> CeremonyDefinition:
    """Create a test ceremony definition."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("complete"),
            guards=(),
            description="Complete",
        ),
    )
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
        ),
    )

    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(),
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def create_test_instance(definition: CeremonyDefinition) -> CeremonyInstance:
    """Create a test ceremony instance."""
    return CeremonyInstance(
        instance_id="test-instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
        correlation_id="test-correlation-1",
        idempotency_keys=frozenset(["key-1", "key-2"]),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_neo4j_adapter():
    """Create mock Neo4j adapter."""
    adapter = MagicMock()
    adapter.load_instance = AsyncMock(return_value=None)
    adapter.find_instances_by_correlation_id = AsyncMock(return_value=[])
    adapter.close = MagicMock()
    return adapter


@pytest.fixture
def rehydration_adapter(mock_neo4j_adapter):
    """Create Neo4jRehydrationAdapter with mocked dependencies."""
    # Create adapter instance and directly replace adapter with mock
    # This avoids trying to create real connections
    adapter = Neo4jRehydrationAdapter.__new__(Neo4jRehydrationAdapter)
    adapter.neo4j_adapter = mock_neo4j_adapter
    return adapter


@pytest.mark.asyncio
async def test_rehydrate_instance_success(rehydration_adapter, mock_neo4j_adapter) -> None:
    """Test successful rehydration of instance."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    mock_neo4j_adapter.load_instance.return_value = instance

    result = await rehydration_adapter.rehydrate_instance("test-instance-1")

    assert result == instance
    assert result.instance_id == "test-instance-1"
    assert result.current_state == "STARTED"
    assert result.step_status.get(StepId("process_step"), StepStatus.PENDING) == StepStatus.COMPLETED
    mock_neo4j_adapter.load_instance.assert_awaited_once_with("test-instance-1")


@pytest.mark.asyncio
async def test_rehydrate_instance_not_found(rehydration_adapter, mock_neo4j_adapter) -> None:
    """Test rehydration when instance not found."""
    mock_neo4j_adapter.load_instance.return_value = None

    result = await rehydration_adapter.rehydrate_instance("non-existent")

    assert result is None
    mock_neo4j_adapter.load_instance.assert_awaited_once_with("non-existent")


@pytest.mark.asyncio
async def test_rehydrate_instances_by_correlation_id(
    rehydration_adapter, mock_neo4j_adapter
) -> None:
    """Test rehydrating multiple instances by correlation ID."""
    definition = create_test_definition()
    instance1 = create_test_instance(definition)
    instance2 = replace(instance1, instance_id="test-instance-2")

    mock_neo4j_adapter.find_instances_by_correlation_id.return_value = [
        instance1,
        instance2,
    ]

    result = await rehydration_adapter.rehydrate_instances_by_correlation_id(
        "test-correlation-1"
    )

    assert len(result) == 2
    assert result[0].instance_id == "test-instance-1"
    assert result[1].instance_id == "test-instance-2"
    mock_neo4j_adapter.find_instances_by_correlation_id.assert_awaited_once_with(
        "test-correlation-1"
    )


@pytest.mark.asyncio
async def test_rehydrate_instance_reconstructs_step_status(
    rehydration_adapter, mock_neo4j_adapter
) -> None:
    """Test that rehydration reconstructs step status (E0.4 AC)."""
    definition = create_test_definition()
    instance = CeremonyInstance(
        instance_id="test-instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
        correlation_id="test-correlation-1",
        idempotency_keys=frozenset(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_neo4j_adapter.load_instance.return_value = instance

    result = await rehydration_adapter.rehydrate_instance("test-instance-1")

    # Verify step status was reconstructed
    assert result.step_status.get(StepId("process_step"), StepStatus.PENDING) == StepStatus.COMPLETED
    # This validates E0.4 AC: rehidratación reconstruye estado desde Neo4j


@pytest.mark.asyncio
async def test_rehydrate_instance_reconstructs_idempotency_keys(
    rehydration_adapter, mock_neo4j_adapter
) -> None:
    """Test that rehydration reconstructs idempotency keys (E0.4 AC)."""
    definition = create_test_definition()
    instance = CeremonyInstance(
        instance_id="test-instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(entries=()),
        correlation_id="test-correlation-1",
        idempotency_keys=frozenset(["key-1", "key-2", "key-3"]),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_neo4j_adapter.load_instance.return_value = instance

    result = await rehydration_adapter.rehydrate_instance("test-instance-1")

    # Verify idempotency keys were reconstructed
    assert len(result.idempotency_keys) == 3
    assert "key-1" in result.idempotency_keys
    assert "key-2" in result.idempotency_keys
    assert "key-3" in result.idempotency_keys
    # This validates E0.4 AC: rehidratación reconstruye estado desde Neo4j
