"""Unit tests for Transition value object."""

import pytest

from datetime import UTC, datetime

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
    State,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
    Timeouts,
)
from core.ceremony_engine.domain.value_objects.transition import Transition
from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger


def _definition_with_guard() -> CeremonyDefinition:
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("complete"),
            guards=(GuardName("all_steps_completed"),),
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


def test_transition_happy_path() -> None:
    """Test creating a valid transition."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger=TransitionTrigger("start_selection"),
        guards=(),
        description="Begin story selection",
    )

    assert transition.from_state == "INITIALIZED"
    assert transition.to_state == "SELECTING"
    assert transition.trigger == TransitionTrigger("start_selection")
    assert transition.guards == ()
    assert transition.description == "Begin story selection"


def test_transition_with_guards() -> None:
    """Test creating a transition with guards."""
    transition = Transition(
        from_state="SELECTING",
        to_state="REVIEWING",
        trigger=TransitionTrigger("selection_complete"),
        guards=(GuardName("selection_valid"), GuardName("capacity_ok")),
        description="Selection complete, ready for review",
    )

    assert len(transition.guards) == 2
    assert GuardName("selection_valid") in transition.guards
    assert GuardName("capacity_ok") in transition.guards


def test_transition_rejects_empty_from_state() -> None:
    """Test that empty from_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition from_state cannot be empty"):
        Transition(
            from_state="",
            to_state="SELECTING",
            trigger=TransitionTrigger("trigger"),
            guards=(),
            description="Description",
        )


def test_transition_rejects_whitespace_from_state() -> None:
    """Test that whitespace-only from_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition from_state cannot be empty"):
        Transition(
            from_state="   ",
            to_state="SELECTING",
            trigger=TransitionTrigger("trigger"),
            guards=(),
            description="Description",
        )


def test_transition_rejects_empty_to_state() -> None:
    """Test that empty to_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition to_state cannot be empty"):
        Transition(
            from_state="INITIALIZED",
            to_state="",
            trigger=TransitionTrigger("trigger"),
            guards=(),
            description="Description",
        )


def test_transition_rejects_invalid_trigger_type() -> None:
    """Test that invalid trigger type raises ValueError."""
    with pytest.raises(ValueError, match="Transition trigger must be a TransitionTrigger"):
        Transition(
            from_state="INITIALIZED",
            to_state="SELECTING",
            trigger="",  # type: ignore[arg-type]
            guards=(),
            description="Description",
        )


def test_transition_rejects_empty_description() -> None:
    """Test that empty description raises ValueError."""
    with pytest.raises(ValueError, match="Transition description cannot be empty"):
        Transition(
            from_state="INITIALIZED",
            to_state="SELECTING",
            trigger=TransitionTrigger("trigger"),
            guards=(),
            description="",
        )


def test_transition_str_representation() -> None:
    """Test string representation of transition."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger=TransitionTrigger("start_selection"),
        guards=(),
        description="Description",
    )
    assert str(transition) == "INITIALIZED -> SELECTING (start_selection)"


def test_transition_is_immutable() -> None:
    """Test that transition is immutable (frozen dataclass)."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger=TransitionTrigger("trigger"),
        guards=(),
        description="Description",
    )

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        transition.from_state = "CHANGED"  # type: ignore[misc]


def test_transition_guards_is_tuple() -> None:
    """Test that guards is stored as tuple (immutable)."""
    guards_list = [GuardName("guard1"), GuardName("guard2")]
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger=TransitionTrigger("trigger"),
        guards=tuple(guards_list),
        description="Description",
    )

    assert isinstance(transition.guards, tuple)
    # Tuple is immutable, so this should not affect the transition
    guards_list.append(GuardName("guard3"))
    assert len(transition.guards) == 2


def test_transition_rejects_invalid_guard_type() -> None:
    """Test that invalid guard type raises ValueError."""
    with pytest.raises(ValueError, match="Transition guard must be GuardName"):
        Transition(
            from_state="INITIALIZED",
            to_state="SELECTING",
            trigger=TransitionTrigger("trigger"),
            guards=("guard1",),  # type: ignore[arg-type]
            description="Description",
        )


def test_transition_evaluate_guards_passes() -> None:
    """Test evaluate_guards when guard passes."""
    definition = _definition_with_guard()
    instance = _instance(definition, completed=True)
    transition = definition.transitions[0]

    result = transition.evaluate_guards(
        instance=instance,
        context=ExecutionContext.empty(),
        guards=definition.guards,
    )

    assert result is True


def test_transition_evaluate_guards_fails() -> None:
    """Test evaluate_guards when guard fails."""
    definition = _definition_with_guard()
    instance = _instance(definition, completed=False)
    transition = definition.transitions[0]

    result = transition.evaluate_guards(
        instance=instance,
        context=ExecutionContext.empty(),
        guards=definition.guards,
    )

    assert result is False


def test_transition_evaluate_guards_missing_guard() -> None:
    """Test evaluate_guards raises for missing guard."""
    definition = _definition_with_guard()
    instance = _instance(definition, completed=True)
    transition = Transition(
        from_state="STARTED",
        to_state="COMPLETED",
        trigger=TransitionTrigger("complete"),
        guards=(GuardName("missing_guard"),),
        description="Complete",
    )

    with pytest.raises(ValueError, match="Guard 'missing_guard' not found"):
        transition.evaluate_guards(
            instance=instance,
            context=ExecutionContext.empty(),
        guards=definition.guards,
        )
