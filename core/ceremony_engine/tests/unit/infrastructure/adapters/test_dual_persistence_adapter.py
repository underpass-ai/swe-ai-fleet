"""Unit tests for DualPersistenceAdapter."""

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
from core.ceremony_engine.infrastructure.adapters.dual_persistence_adapter import (
    DualPersistenceAdapter,
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
    adapter.save_instance = AsyncMock()
    adapter.load_instance = AsyncMock(return_value=None)
    adapter.find_instances_by_correlation_id = AsyncMock(return_value=[])
    adapter.close = MagicMock()
    return adapter


@pytest.fixture
def mock_valkey_adapter():
    """Create mock Valkey adapter."""
    adapter = MagicMock()
    adapter.save_instance = AsyncMock()
    adapter.load_instance = AsyncMock(return_value=None)
    adapter.find_instances_by_correlation_id = AsyncMock(return_value=[])
    adapter.close = MagicMock()
    return adapter


@pytest.fixture
def dual_adapter(mock_neo4j_adapter, mock_valkey_adapter):
    """Create DualPersistenceAdapter with mocked dependencies."""
    # Create adapter instance and directly replace adapters with mocks
    # This avoids trying to create real connections
    adapter = DualPersistenceAdapter.__new__(DualPersistenceAdapter)
    adapter.neo4j = mock_neo4j_adapter
    adapter.valkey = mock_valkey_adapter
    return adapter


@pytest.mark.asyncio
async def test_save_instance_dual_write_success(dual_adapter, mock_neo4j_adapter, mock_valkey_adapter) -> None:
    """Test saving instance with successful dual write."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    await dual_adapter.save_instance(instance)

    # Verify Valkey write was called (source of truth)
    mock_valkey_adapter.save_instance.assert_awaited_once_with(instance)
    # Verify Neo4j write was called
    mock_neo4j_adapter.save_instance.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_save_instance_valkey_fails(dual_adapter, mock_neo4j_adapter, mock_valkey_adapter) -> None:
    """Test that Valkey failure fails the operation (fail-fast)."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    # Make Valkey fail
    mock_valkey_adapter.save_instance.side_effect = Exception("Valkey error")

    with pytest.raises(Exception, match="Valkey error"):
        await dual_adapter.save_instance(instance)

    # Verify Neo4j was NOT called (Valkey failed first)
    mock_neo4j_adapter.save_instance.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_instance_neo4j_fails_but_valkey_succeeds(
    dual_adapter, mock_neo4j_adapter, mock_valkey_adapter
) -> None:
    """Test that Neo4j failure doesn't fail the operation (Valkey succeeded)."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    # Make Neo4j fail but Valkey succeed
    mock_neo4j_adapter.save_instance.side_effect = Exception("Neo4j error")

    # Operation should succeed (Valkey write succeeded)
    await dual_adapter.save_instance(instance)

    # Verify both were called
    mock_valkey_adapter.save_instance.assert_awaited_once_with(instance)
    mock_neo4j_adapter.save_instance.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_load_instance_from_valkey(dual_adapter, mock_valkey_adapter) -> None:
    """Test loading instance from Valkey."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    mock_valkey_adapter.load_instance.return_value = instance

    result = await dual_adapter.load_instance("test-instance-1")

    assert result == instance
    mock_valkey_adapter.load_instance.assert_awaited_once_with("test-instance-1")


@pytest.mark.asyncio
async def test_find_instances_by_correlation_id(dual_adapter, mock_valkey_adapter) -> None:
    """Test finding instances by correlation ID."""
    definition = create_test_definition()
    instance1 = create_test_instance(definition)
    instance2 = replace(instance1, instance_id="test-instance-2")

    mock_valkey_adapter.find_instances_by_correlation_id.return_value = [
        instance1,
        instance2,
    ]

    result = await dual_adapter.find_instances_by_correlation_id("test-correlation-1")

    assert len(result) == 2
    assert result[0].instance_id == "test-instance-1"
    assert result[1].instance_id == "test-instance-2"
    mock_valkey_adapter.find_instances_by_correlation_id.assert_awaited_once_with(
        "test-correlation-1"
    )


@pytest.mark.asyncio
async def test_close_closes_both_adapters(dual_adapter, mock_neo4j_adapter, mock_valkey_adapter) -> None:
    """Test that close() closes both adapters."""
    dual_adapter.close()

    mock_neo4j_adapter.close.assert_called_once()
    mock_valkey_adapter.close.assert_called_once()
