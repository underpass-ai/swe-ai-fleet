"""Unit tests for CeremonyDefinition entity."""

import pytest

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects import (
    Guard,
    GuardType,
    Inputs,
    Output,
    RetryPolicy,
    Role,
    State,
    Step,
    StepHandlerType,
    Timeouts,
    Transition,
)


def test_ceremony_definition_happy_path() -> None:
    """Test creating a valid ceremony definition."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger="complete",
            guards=(),
            description="Complete",
        ),
    )
    steps = (
        Step(
            id="process",
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "echo"},
        ),
    )

    definition = CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(Role(id="SYSTEM", description="System", allowed_actions=()),),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )

    assert definition.name == "test_ceremony"
    assert definition.version == "1.0"
    assert definition.get_initial_state().id == "STARTED"


def test_ceremony_definition_rejects_invalid_version() -> None:
    """Test that invalid version raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    with pytest.raises(ValueError, match="Unsupported ceremony definition version"):
        CeremonyDefinition(
            version="2.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_empty_name() -> None:
    """Test that empty name raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    with pytest.raises(ValueError, match="Ceremony name cannot be empty"):
        CeremonyDefinition(
            version="1.0",
            name="",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_invalid_name_format() -> None:
    """Test that invalid name format (not snake_case) raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    with pytest.raises(ValueError, match="Ceremony name must be snake_case"):
        CeremonyDefinition(
            version="1.0",
            name="Invalid Name",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_no_initial_state() -> None:
    """Test that no initial state raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=False, terminal=False),)
    with pytest.raises(ValueError, match="Exactly one state must have initial=True"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_multiple_initial_states() -> None:
    """Test that multiple initial states raises ValueError."""
    states = (
        State(id="STARTED1", description="Started1", initial=True, terminal=False),
        State(id="STARTED2", description="Started2", initial=True, terminal=False),
    )
    with pytest.raises(ValueError, match="Exactly one state must have initial=True"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_terminal_state_with_outgoing_transition() -> None:
    """Test that terminal state with outgoing transition raises ValueError."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="COMPLETED",  # Terminal state
            to_state="STARTED",
            trigger="restart",
            guards=(),
            description="Restart",
        ),
    )
    with pytest.raises(ValueError, match="Terminal state.*cannot have outgoing transitions"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=transitions,
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_transition_with_invalid_from_state() -> None:
    """Test that transition with invalid from_state raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    transitions = (
        Transition(
            from_state="INVALID",
            to_state="STARTED",
            trigger="trigger",
            guards=(),
            description="Description",
        ),
    )
    with pytest.raises(ValueError, match="references non-existent state"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=transitions,
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_step_with_invalid_state() -> None:
    """Test that step with invalid state raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    steps = (
        Step(
            id="process",
            state="INVALID",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "echo"},
        ),
    )
    with pytest.raises(ValueError, match="references non-existent state"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=steps,
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_transition_with_invalid_guard() -> None:
    """Test that transition with invalid guard raises ValueError."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger="complete",
            guards=("invalid_guard",),
            description="Complete",
        ),
    )
    with pytest.raises(ValueError, match="references non-existent guard"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=transitions,
            steps=(),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_rejects_role_with_invalid_action() -> None:
    """Test that role with invalid allowed_action raises ValueError."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    roles = (Role(id="PO", description="Product Owner", allowed_actions=("invalid_action",)),)
    with pytest.raises(ValueError, match="references non-existent action"):
        CeremonyDefinition(
            version="1.0",
            name="test",
            description="Test",
            inputs=Inputs(required=(), optional=()),
            outputs={},
            states=states,
            transitions=(),
            steps=(),
            guards={},
            roles=roles,
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )


def test_ceremony_definition_allows_role_with_valid_step_action() -> None:
    """Test that role with valid step action is accepted."""
    states = (State(id="STARTED", description="Started", initial=True, terminal=False),)
    steps = (
        Step(
            id="process",
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "echo"},
        ),
    )
    roles = (Role(id="PO", description="Product Owner", allowed_actions=("process",)),)

    definition = CeremonyDefinition(
        version="1.0",
        name="test",
        description="Test",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=(),
        steps=steps,
        guards={},
        roles=roles,
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )

    assert definition.roles[0].allowed_actions == ("process",)


def test_ceremony_definition_allows_role_with_valid_trigger_action() -> None:
    """Test that role with valid trigger action is accepted."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger="complete",
            guards=(),
            description="Complete",
        ),
    )
    roles = (Role(id="PO", description="Product Owner", allowed_actions=("complete",)),)

    definition = CeremonyDefinition(
        version="1.0",
        name="test",
        description="Test",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=(),
        guards={},
        roles=roles,
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )

    assert definition.roles[0].allowed_actions == ("complete",)


def test_ceremony_definition_get_initial_state() -> None:
    """Test get_initial_state method."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )

    definition = CeremonyDefinition(
        version="1.0",
        name="test",
        description="Test",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=(),
        steps=(),
        guards={},
        roles=(),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )

    initial_state = definition.get_initial_state()
    assert initial_state.id == "STARTED"
    assert initial_state.initial is True


def test_ceremony_definition_get_state_by_id() -> None:
    """Test get_state_by_id method."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )

    definition = CeremonyDefinition(
        version="1.0",
        name="test",
        description="Test",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=(),
        steps=(),
        guards={},
        roles=(),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )

    state = definition.get_state_by_id("STARTED")
    assert state is not None
    assert state.id == "STARTED"

    state_not_found = definition.get_state_by_id("INVALID")
    assert state_not_found is None
