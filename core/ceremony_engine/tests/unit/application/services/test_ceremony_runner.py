"""Unit tests for CeremonyRunner."""

from dataclasses import replace
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Guard,
    GuardName,
    GuardType,
    Inputs,
    Role,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepResult,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
    StepOutputMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState
import pytest


def create_messaging_port() -> AsyncMock:
    """Create mock MessagingPort."""
    return AsyncMock(spec=MessagingPort)


def create_test_definition() -> CeremonyDefinition:
    """Create a test ceremony definition."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="PROCESSING", description="Processing", initial=False, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="PROCESSING",
            trigger=TransitionTrigger("start_processing"),
            guards=(GuardName("all_steps_completed"),),
            description="Start processing",
        ),
        Transition(
            from_state="PROCESSING",
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
    guards = {
        GuardName("all_steps_completed"): Guard(
            name=GuardName("all_steps_completed"),
            type=GuardType.AUTOMATED,
            check="all_steps_completed",
        ),
    }

    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=steps,
        guards=guards,
        roles=(),
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def create_definition_with_role(role_actions: tuple[str, ...]) -> CeremonyDefinition:
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "echo", "role": "PO"},
        ),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("approve"),
            guards=(),
            description="Approve",
        ),
    )
    return CeremonyDefinition(
        version="1.0",
        name="role_ceremony",
        description="Role ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=(
            State(id="STARTED", description="Started", initial=True, terminal=False),
            State(id="COMPLETED", description="Completed", initial=False, terminal=True),
        ),
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(Role(id="PO", description="Product Owner", allowed_actions=role_actions),),
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def create_test_instance(definition: CeremonyDefinition) -> CeremonyInstance:
    """Create a test ceremony instance."""
    return CeremonyInstance(
        instance_id="test-instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(entries=()),
        step_outputs=StepOutputMap(entries=()),
        correlation_id="test-correlation-1",
        idempotency_keys=frozenset(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_execute_step_happy_path() -> None:
    """Test executing a step successfully."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    # Mock step handler port
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={"result": "success"},
    )

    # Mock persistence port
    persistence_port = AsyncMock(spec=PersistencePort)

    messaging_port = create_messaging_port()
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step was executed
    step_handler_port.execute_step.assert_awaited_once()
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED

    # Verify persistence was called
    persistence_port.save_instance.assert_awaited_once()
    # Verify events were published (step executed and potentially transition applied)
    assert messaging_port.publish_event.await_count >= 1
    # Check that step executed event was published
    call_args_list = messaging_port.publish_event.call_args_list
    step_executed_calls = [
        call for call in call_args_list
        if call.kwargs.get("subject") == "ceremony.step.executed"
    ]
    assert len(step_executed_calls) == 1


@pytest.mark.asyncio
async def test_execute_step_idempotency_completed_skips_execution() -> None:
    """Test idempotency COMPLETED skips step execution."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = IdempotencyState.COMPLETED

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    assert result == instance
    step_handler_port.execute_step.assert_not_awaited()
    idempotency_port.mark_in_progress.assert_not_awaited()
    idempotency_port.mark_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_step_idempotency_in_progress_not_stale_skips() -> None:
    """Test idempotency IN_PROGRESS (not stale) skips execution."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = IdempotencyState.IN_PROGRESS
    idempotency_port.is_stale.return_value = False

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    assert result == instance
    step_handler_port.execute_step.assert_not_awaited()
    idempotency_port.mark_in_progress.assert_not_awaited()
    idempotency_port.mark_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_step_idempotency_in_progress_stale_executes() -> None:
    """Test idempotency IN_PROGRESS stale allows execution."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={"result": "success"},
    )
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = IdempotencyState.IN_PROGRESS
    idempotency_port.is_stale.return_value = True
    idempotency_port.mark_in_progress.return_value = False

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    step_handler_port.execute_step.assert_awaited_once()
    idempotency_port.mark_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_step_marks_idempotency_completed_on_success() -> None:
    """Test idempotency is marked completed on successful step."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={"result": "success"},
    )
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    idempotency_port.mark_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_step_failure_does_not_mark_idempotency_completed() -> None:
    """Test failed step does not mark idempotency completed."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.FAILED,
        output={},
        error_message="Step failed",
    )
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    assert result.get_step_status(StepId("process_step")) == StepStatus.FAILED
    idempotency_port.mark_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_idempotency_completed_requires_key_when_port_set() -> None:
    """Test _mark_idempotency_completed fails fast without key."""
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        await runner._mark_idempotency_completed("")


@pytest.mark.asyncio
async def test_execute_step_invalid_state() -> None:
    """Test executing a step when instance is in wrong state."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Change state to wrong state
    from dataclasses import replace

    instance = replace(instance, current_state="PROCESSING")

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="requires state 'STARTED'"):
        await runner.execute_step(instance, StepId("process_step"))


@pytest.mark.asyncio
async def test_execute_step_not_executable_status() -> None:
    """Test executing a step when step status is not executable."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Set step status to IN_PROGRESS (not executable)
    instance = replace(
        instance,
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.IN_PROGRESS),)
        ),
    )

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="cannot be executed from status"):
        await runner.execute_step(instance, StepId("process_step"))


@pytest.mark.asyncio
async def test_execute_step_terminal_state() -> None:
    """Test executing a step when instance is in terminal state (step not in that state)."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Change to terminal state
    instance = replace(instance, current_state="COMPLETED")

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    # Step requires STARTED state, but instance is in COMPLETED
    with pytest.raises(ValueError, match="requires state 'STARTED'"):
        await runner.execute_step(instance, StepId("process_step"))


@pytest.mark.asyncio
async def test_execute_step_not_found() -> None:
    """Test executing a step that doesn't exist."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="Step 'nonexistent' not found"):
        await runner.execute_step(instance, StepId("nonexistent"))


@pytest.mark.asyncio
async def test_transition_state_happy_path() -> None:
    """Test transitioning state successfully."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Complete step so guard passes
    instance = replace(
        instance,
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
    )

    persistence_port = AsyncMock(spec=PersistencePort)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
        persistence_port=persistence_port,
    )

    result = await runner.transition_state(instance, TransitionTrigger("start_processing"))

    assert result.current_state == "PROCESSING"
    persistence_port.save_instance.assert_awaited_once()


@pytest.mark.asyncio
async def test_transition_state_idempotency_completed_skips() -> None:
    """Test idempotency COMPLETED skips transition execution."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = IdempotencyState.COMPLETED

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.transition_state(instance, TransitionTrigger("start_processing"))

    assert result == instance
    idempotency_port.mark_in_progress.assert_not_awaited()
    idempotency_port.mark_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_transition_state_marks_idempotency_completed() -> None:
    """Test transition marks idempotency completed."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    instance = replace(
        instance,
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
    )

    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
        idempotency_port=idempotency_port,
    )

    result = await runner.transition_state(instance, TransitionTrigger("start_processing"))

    assert result.current_state == "PROCESSING"
    idempotency_port.mark_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_transition_state_guards_fail() -> None:
    """Test transitioning when guards fail."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Step not completed, so guard fails

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="guards not satisfied"):
        await runner.transition_state(instance, TransitionTrigger("start_processing"))


@pytest.mark.asyncio
async def test_transition_state_not_found() -> None:
    """Test transitioning with invalid trigger."""
    definition = create_test_definition()
    instance = create_test_instance(definition)

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="Transition with trigger 'invalid' not found"):
        await runner.transition_state(instance, TransitionTrigger("invalid"))


@pytest.mark.asyncio
async def test_evaluate_automated_guard_all_steps_completed() -> None:
    """Test evaluating automated guard: all_steps_completed."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Complete all steps
    instance = replace(
        instance,
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
    )

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    transition = definition.transitions[0]  # start_processing transition

    guards_passed = runner._evaluate_guards(instance, transition, ExecutionContext.empty())

    assert guards_passed is True


@pytest.mark.asyncio
async def test_evaluate_automated_guard_all_steps_not_completed() -> None:
    """Test evaluating automated guard when steps not completed."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Steps not completed

    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    transition = definition.transitions[0]  # start_processing transition

    guards_passed = runner._evaluate_guards(instance, transition, ExecutionContext.empty())

    assert guards_passed is False


@pytest.mark.asyncio
async def test_evaluate_human_guard_approved() -> None:
    """Test evaluating human guard when approved."""
    definition = create_test_definition()
    # Add human guard
    guards = {
        **definition.guards,
        GuardName("human_approval"): Guard(
            name=GuardName("human_approval"),
            type=GuardType.HUMAN,
            check="Requires PO approval",
            role="product_owner",
        ),
    }
    definition = definition.with_guards(guards)

    transitions = (
        Transition(
            from_state="STARTED",
            to_state="PROCESSING",
            trigger=TransitionTrigger("start_processing"),
            guards=(GuardName("human_approval"),),
            description="Start processing",
        ),
    )
    definition = definition.with_transitions(transitions)

    instance = create_test_instance(definition)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    transition = definition.transitions[0]

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"human_approval": True},
            ),
        )
    )
    guards_passed = runner._evaluate_guards(instance, transition, context)

    assert guards_passed is True


@pytest.mark.asyncio
async def test_evaluate_human_guard_not_approved() -> None:
    """Test evaluating human guard when not approved."""
    definition = create_test_definition()
    # Add human guard
    guards = {
        **definition.guards,
        GuardName("human_approval"): Guard(
            name=GuardName("human_approval"),
            type=GuardType.HUMAN,
            check="Requires PO approval",
            role="product_owner",
        ),
    }
    definition = definition.with_guards(guards)

    transitions = (
        Transition(
            from_state="STARTED",
            to_state="PROCESSING",
            trigger=TransitionTrigger("start_processing"),
            guards=(GuardName("human_approval"),),
            description="Start processing",
        ),
    )
    definition = definition.with_transitions(transitions)

    instance = create_test_instance(definition)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    transition = definition.transitions[0]

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={},
            ),
        )
    )
    guards_passed = runner._evaluate_guards(instance, transition, context)

    assert guards_passed is False


@pytest.mark.asyncio
async def test_execute_step_triggers_transition() -> None:
    """Test that executing a step triggers transition if guards pass."""
    definition = create_test_definition()
    instance = create_test_instance(definition)
    # Step is PENDING (not completed yet)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={"result": "success"},
    )

    persistence_port = AsyncMock(spec=PersistencePort)
    messaging_port = create_messaging_port()
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )

    # Execute step (should trigger transition since guard passes after step completes)
    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step completed
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    # Verify transition occurred (state changed to PROCESSING)
    assert result.current_state == "PROCESSING"
    assert messaging_port.publish_event.await_count == 2
    subjects = [call.kwargs["subject"] for call in messaging_port.publish_event.call_args_list]
    assert subjects == ["ceremony.step.executed", "ceremony.transition.applied"]


@pytest.mark.asyncio
async def test_runner_requires_step_handler_port() -> None:
    """Test that runner requires step_handler_port."""
    with pytest.raises(ValueError, match="step_handler_port is required"):
        CeremonyRunner(
            step_handler_port=None,  # type: ignore[arg-type]
            messaging_port=create_messaging_port(),
        )


@pytest.mark.asyncio
async def test_runner_requires_messaging_port() -> None:
    """Test that runner requires messaging_port."""
    with pytest.raises(ValueError, match="messaging_port is required"):
        CeremonyRunner(
            step_handler_port=AsyncMock(spec=StepHandlerPort),
            messaging_port=None,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_execute_step_rejects_role_not_allowed() -> None:
    definition = create_definition_with_role(("approve",))
    instance = create_test_instance(definition)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    context = ExecutionContext.builder().build()

    with pytest.raises(ValueError, match="not allowed to execute step"):
        await runner.execute_step(instance, StepId("process_step"), context)


@pytest.mark.asyncio
async def test_transition_rejects_role_not_allowed() -> None:
    definition = create_definition_with_role(("process_step",))
    instance = create_test_instance(definition)
    runner = CeremonyRunner(
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        messaging_port=create_messaging_port(),
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"role": "PO"}),)
    )

    with pytest.raises(ValueError, match="not allowed to execute trigger"):
        await runner.transition_state(instance, TransitionTrigger("approve"), context)


@pytest.mark.asyncio
async def test_execute_step_with_retry_succeeds_on_retry() -> None:
    """Test that step retries on failure and succeeds on second attempt."""
    from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy

    definition = create_test_definition()
    # Add retry policy to step
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            retry=RetryPolicy(max_attempts=3, backoff_seconds=0, exponential_backoff=False),
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    # Mock step handler: fail first time, succeed second time
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.side_effect = [
        StepResult(status=StepStatus.FAILED, output={}, error_message="First attempt failed"),
        StepResult(status=StepStatus.COMPLETED, output={"result": "success"}),
    ]

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step succeeded after retry
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    # Verify handler was called twice
    assert step_handler_port.execute_step.await_count == 2


@pytest.mark.asyncio
async def test_execute_step_with_retry_exhausts_attempts() -> None:
    """Test that step fails after exhausting all retry attempts."""
    from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy

    definition = create_test_definition()
    # Add retry policy to step
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            retry=RetryPolicy(max_attempts=2, backoff_seconds=0, exponential_backoff=False),
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    # Mock step handler: always fail
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.FAILED, output={}, error_message="Step failed"
    )

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step failed after all retries
    assert result.get_step_status(StepId("process_step")) == StepStatus.FAILED
    # Verify handler was called max_attempts times
    assert step_handler_port.execute_step.await_count == 2


@pytest.mark.asyncio
async def test_execute_step_with_exponential_backoff() -> None:
    """Test that exponential backoff is applied correctly."""
    import time

    from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy

    definition = create_test_definition()
    # Add retry policy with exponential backoff
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            retry=RetryPolicy(max_attempts=3, backoff_seconds=1, exponential_backoff=True),
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    # Mock step handler: fail twice, succeed third time
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.side_effect = [
        StepResult(status=StepStatus.FAILED, output={}, error_message="First attempt failed"),
        StepResult(status=StepStatus.FAILED, output={}, error_message="Second attempt failed"),
        StepResult(status=StepStatus.COMPLETED, output={"result": "success"}),
    ]

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    start_time = time.time()
    result = await runner.execute_step(instance, StepId("process_step"))
    elapsed_time = time.time() - start_time

    # Verify step succeeded
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    # Verify handler was called 3 times
    assert step_handler_port.execute_step.await_count == 3
    # Verify exponential backoff was applied (1s after first failure, 2s after second)
    # Allow some tolerance for test execution time
    assert elapsed_time >= 2.5  # At least 1s + 2s backoff


@pytest.mark.asyncio
async def test_execute_step_with_timeout() -> None:
    """Test that step execution times out correctly."""
    import asyncio

    definition = create_test_definition()
    # Add timeout to step
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            timeout_seconds=1,
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    # Mock step handler: delay longer than timeout
    async def slow_step(step: Step, context: ExecutionContext) -> StepResult:
        await asyncio.sleep(2)  # Longer than 1s timeout
        return StepResult(status=StepStatus.COMPLETED, output={})

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.side_effect = slow_step

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step failed due to timeout
    assert result.get_step_status(StepId("process_step")) == StepStatus.FAILED


@pytest.mark.asyncio
async def test_execute_step_timeout_exceeds_step_max() -> None:
    """Test that step timeout validation fails if exceeds step_max."""
    definition = create_test_definition()
    # Step timeout exceeds step_max (600)
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            timeout_seconds=1000,  # Exceeds step_max of 600
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    with pytest.raises(ValueError, match="exceeds ceremony step_max"):
        await runner.execute_step(instance, StepId("process_step"))


@pytest.mark.asyncio
async def test_execute_step_uses_default_timeout() -> None:
    """Test that step uses default timeout when not specified."""
    definition = create_test_definition()
    # Step without timeout_seconds
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
            # No timeout_seconds, should use step_default (300)
        ),
    )
    definition = definition.with_steps(steps)

    instance = create_test_instance(definition)

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED, output={"result": "success"}
    )

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step completed (timeout would have failed if not applied correctly)
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_step_uses_default_retry_policy() -> None:
    """Test that step uses default retry policy from definition when step has none."""
    from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy

    definition = create_test_definition()
    # Add default retry policy to definition
    retry_policies = {
        "default": RetryPolicy(max_attempts=2, backoff_seconds=0, exponential_backoff=False),
    }
    definition = definition.with_retry_policies(retry_policies)

    instance = create_test_instance(definition)

    # Mock step handler: fail first time, succeed second time
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.side_effect = [
        StepResult(status=StepStatus.FAILED, output={}, error_message="First attempt failed"),
        StepResult(status=StepStatus.COMPLETED, output={"result": "success"}),
    ]

    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=create_messaging_port(),
    )

    result = await runner.execute_step(instance, StepId("process_step"))

    # Verify step succeeded after retry using default policy
    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    # Verify handler was called twice (retry from default policy)
    assert step_handler_port.execute_step.await_count == 2
