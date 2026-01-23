"""Unit tests for Guard value object."""

import pytest
from datetime import UTC, datetime

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    GuardName,
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
from core.ceremony_engine.domain.value_objects.guard import Guard
from core.ceremony_engine.domain.value_objects.guard_type import GuardType


def _definition() -> CeremonyDefinition:
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
            id=StepId("process"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "echo"},
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
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )


def _instance(definition: CeremonyDefinition, completed: bool) -> CeremonyInstance:
    now = datetime.now(UTC)
    status = StepStatus.COMPLETED if completed else StepStatus.PENDING
    return CeremonyInstance(
        instance_id="instance-123",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process"), status=status),)
        ),
        correlation_id="corr-123",
        idempotency_keys=frozenset(),
        created_at=now,
        updated_at=now,
    )


def test_guard_automated_happy_path() -> None:
    """Test creating a valid automated guard."""
    guard = Guard(
        name=GuardName("selection_valid"),
        type=GuardType.AUTOMATED,
        check="scored_stories.length >= 1",
    )

    assert guard.name == GuardName("selection_valid")
    assert guard.type == GuardType.AUTOMATED
    assert guard.check == "scored_stories.length >= 1"
    assert guard.role is None
    assert guard.threshold is None


def test_guard_human_happy_path() -> None:
    """Test creating a valid human guard."""
    guard = Guard(
        name=GuardName("po_approved"),
        type=GuardType.HUMAN,
        check="PO has explicitly approved",
        role="PO",
    )

    assert guard.name == GuardName("po_approved")
    assert guard.type == GuardType.HUMAN
    assert guard.check == "PO has explicitly approved"
    assert guard.role == "PO"


def test_guard_with_threshold() -> None:
    """Test creating a guard with threshold."""
    guard = Guard(
        name=GuardName("score_threshold"),
        type=GuardType.AUTOMATED,
        check="score >= threshold",
        threshold=75.0,
    )

    assert guard.threshold == pytest.approx(75.0)


def test_guard_rejects_invalid_name_type() -> None:
    """Test that invalid name type raises ValueError."""
    with pytest.raises(ValueError, match="Guard name must be GuardName"):
        Guard(name="guard_name", type=GuardType.AUTOMATED, check="expression")  # type: ignore[arg-type]


def test_guard_rejects_whitespace_name() -> None:
    """Test that whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="GuardName value cannot be empty"):
        Guard(name=GuardName("   "), type=GuardType.AUTOMATED, check="expression")


def test_guard_rejects_empty_check() -> None:
    """Test that empty check raises ValueError."""
    with pytest.raises(ValueError, match="Guard check cannot be empty"):
        Guard(name=GuardName("guard_name"), type=GuardType.AUTOMATED, check="")


def test_guard_rejects_whitespace_check() -> None:
    """Test that whitespace-only check raises ValueError."""
    with pytest.raises(ValueError, match="Guard check cannot be empty"):
        Guard(name=GuardName("guard_name"), type=GuardType.AUTOMATED, check="   ")


def test_guard_is_immutable() -> None:
    """Test that guard is immutable (frozen dataclass)."""
    guard = Guard(name=GuardName("test"), type=GuardType.AUTOMATED, check="expression")

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        guard.name = "changed"  # type: ignore[misc]


def test_guard_evaluate_all_steps_completed() -> None:
    """Test evaluate with all_steps_completed."""
    definition = _definition()
    instance = _instance(definition, completed=True)
    guard = Guard(name=GuardName("all_done"), type=GuardType.AUTOMATED, check="all_steps_completed")

    assert guard.evaluate(instance, ExecutionContext.empty()) is True


def test_guard_evaluate_all_steps_not_completed() -> None:
    """Test evaluate when not all steps are completed."""
    definition = _definition()
    instance = _instance(definition, completed=False)
    guard = Guard(name=GuardName("all_done"), type=GuardType.AUTOMATED, check="all_steps_completed")

    assert guard.evaluate(instance, ExecutionContext.empty()) is False


def test_guard_evaluate_step_status_matches() -> None:
    """Test evaluate for step_status guard."""
    definition = _definition()
    instance = _instance(definition, completed=True)
    guard = Guard(
        name=GuardName("process_done"),
        type=GuardType.AUTOMATED,
        check="step_status:process:completed",
    )

    assert guard.evaluate(instance, ExecutionContext.empty()) is True


def test_guard_evaluate_step_status_missing_step() -> None:
    """Test evaluate for step_status with missing step."""
    definition = _definition()
    instance = _instance(definition, completed=True)
    guard = Guard(
        name=GuardName("missing_step"),
        type=GuardType.AUTOMATED,
        check="step_status:missing:completed",
    )

    assert guard.evaluate(instance, ExecutionContext.empty()) is False


def test_guard_evaluate_human_approval() -> None:
    """Test evaluate for human approval."""
    definition = _definition()
    instance = _instance(definition, completed=False)
    guard = Guard(
        name=GuardName("human_approval"),
        type=GuardType.HUMAN,
        check="Requires approval",
        role="product_owner",
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"human_approval": True},
            ),
        )
    )
    assert guard.evaluate(instance, context) is True


def test_guard_evaluate_human_approval_missing_context() -> None:
    """Test evaluate for human approval with missing context."""
    definition = _definition()
    instance = _instance(definition, completed=False)
    guard = Guard(
        name=GuardName("human_approval"),
        type=GuardType.HUMAN,
        check="Requires approval",
        role="product_owner",
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value="invalid",
            ),
        )
    )
    assert guard.evaluate(instance, context) is False


def test_guard_evaluate_rejects_unsupported_check() -> None:
    """Test evaluate rejects unsupported automated check."""
    definition = _definition()
    instance = _instance(definition, completed=False)
    guard = Guard(
        name=GuardName("unsupported"),
        type=GuardType.AUTOMATED,
        check="unknown_expression",
    )

    with pytest.raises(ValueError, match="Unsupported guard check"):
        guard.evaluate(instance, ExecutionContext.empty())
