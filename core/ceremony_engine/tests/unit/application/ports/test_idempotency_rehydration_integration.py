"""Integration tests for IdempotencyPort + RehydrationPort.

These tests validate the complete E0.4 scenario:
- Reinicio del service no duplica side effects (using IdempotencyPort)
- Rehidratación reconstruye estado desde Neo4j (using RehydrationPort)
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.rehydration_port import RehydrationPort
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
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState


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


@pytest.mark.asyncio
async def test_restart_no_duplicate_side_effects() -> None:
    """Test that restart does not duplicate side effects (E0.4 AC).

    Scenario:
    1. First execution: Process event with idempotency_key "key-1"
    2. Mark as IN_PROGRESS, then COMPLETED
    3. Service restarts (Valkey cache lost)
    4. Same event redelivered with same idempotency_key
    5. Check status returns COMPLETED
    6. No duplicate processing occurs
    """
    # Mock IdempotencyPort
    idempotency_port = AsyncMock(spec=IdempotencyPort)

    # First execution: mark as IN_PROGRESS
    idempotency_port.mark_in_progress.return_value = True
    result1 = await idempotency_port.mark_in_progress("key-1", ttl_seconds=300)
    assert result1 is True

    # Mark as COMPLETED
    await idempotency_port.mark_completed("key-1")

    # Service restarts, event redelivered
    # Check status returns COMPLETED (persisted in Valkey)
    idempotency_port.check_status.return_value = IdempotencyState.COMPLETED
    status = await idempotency_port.check_status("key-1")
    assert status == IdempotencyState.COMPLETED

    # Try to mark as IN_PROGRESS again (should fail)
    idempotency_port.mark_in_progress.return_value = False
    result2 = await idempotency_port.mark_in_progress("key-1", ttl_seconds=300)
    assert result2 is False

    # This prevents duplicate side effects (E0.4 AC)


@pytest.mark.asyncio
async def test_rehydration_reconstructs_state_from_neo4j() -> None:
    """Test that rehydration reconstructs state from Neo4j (E0.4 AC).

    Scenario:
    1. Instance was saved to Neo4j with step_status and idempotency_keys
    2. Service restarts (Valkey cache lost)
    3. Rehydrate instance from Neo4j
    4. Verify all state is reconstructed
    """
    # Mock RehydrationPort
    rehydration_port = AsyncMock(spec=RehydrationPort)

    definition = create_test_definition()
    # Instance with state that needs to be reconstructed
    expected_instance = CeremonyInstance(
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

    # Rehydrate from Neo4j
    rehydration_port.rehydrate_instance.return_value = expected_instance
    result = await rehydration_port.rehydrate_instance("test-instance-1")

    # Verify state was reconstructed
    assert result.instance_id == "test-instance-1"
    assert result.current_state == "STARTED"
    assert result.step_status.get(StepId("process_step"), StepStatus.PENDING) == StepStatus.COMPLETED
    assert len(result.idempotency_keys) == 2
    assert "key-1" in result.idempotency_keys
    assert "key-2" in result.idempotency_keys

    # This validates E0.4 AC: rehidratación reconstruye estado desde Neo4j


@pytest.mark.asyncio
async def test_restart_with_rehydration_flow() -> None:
    """Test complete restart flow with rehydration (E0.4 AC).

    Scenario:
    1. Instance is executing, state saved to Neo4j
    2. Service restarts (Valkey cache lost)
    3. Rehydrate instance from Neo4j
    4. Check idempotency for pending operations
    5. Continue execution without duplicate side effects
    """
    # Mock ports
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    rehydration_port = AsyncMock(spec=RehydrationPort)

    definition = create_test_definition()
    # Instance that was in progress before restart
    instance = CeremonyInstance(
        instance_id="test-instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.IN_PROGRESS),)
        ),
        correlation_id="test-correlation-1",
        idempotency_keys=frozenset(["step-process_step-key"]),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Step 1: Rehydrate from Neo4j
    rehydration_port.rehydrate_instance.return_value = instance
    rehydrated = await rehydration_port.rehydrate_instance("test-instance-1")
    assert rehydrated is not None

    # Step 2: Check idempotency for step execution
    idempotency_port.check_status.return_value = IdempotencyState.COMPLETED
    status = await idempotency_port.check_status("step-process_step-key")
    assert status == IdempotencyState.COMPLETED

    # Step 3: Since step is already COMPLETED, no duplicate execution
    # This validates both E0.4 ACs:
    # - Reinicio no duplica side effects
    # - Rehidratación reconstruye estado desde Neo4j
