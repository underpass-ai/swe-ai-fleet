"""Unit tests for CeremonyInstance entity."""

import pytest
from datetime import datetime, UTC

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
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
    Timeouts,
    Transition,
    TransitionTrigger,
)


def create_minimal_definition() -> CeremonyDefinition:
    """Create a minimal valid CeremonyDefinition for testing."""
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
        roles=(Role(id="SYSTEM", description="System", allowed_actions=()),),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )


class TestCeremonyInstance:
    """Test cases for CeremonyInstance entity."""

    def test_ceremony_instance_happy_path(self) -> None:
        """Test creating a valid ceremony instance."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.PENDING),)
            ),
            correlation_id="corr-123",
            idempotency_keys=frozenset(["key-1", "key-2"]),
            created_at=now,
            updated_at=now,
        )

        assert instance.instance_id == "instance-123"
        assert instance.current_state == "STARTED"
        assert instance.step_status == StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.PENDING),)
        )
        assert instance.correlation_id == "corr-123"
        assert instance.idempotency_keys == frozenset(["key-1", "key-2"])

    def test_ceremony_instance_rejects_empty_instance_id(self) -> None:
        """Test that empty instance_id is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="instance_id cannot be empty"):
            CeremonyInstance(
                instance_id="",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_invalid_definition_type(self) -> None:
        """Test that invalid definition type is rejected."""
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="definition must be a CeremonyDefinition"):
            CeremonyInstance(
                instance_id="instance-123",
                definition="not a definition",  # type: ignore[arg-type]
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_invalid_step_status_type(self) -> None:
        """Test that invalid step_status type is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="step_status must be a StepStatusMap"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status={"process": StepStatus.PENDING},  # type: ignore[arg-type]
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_invalid_current_state(self) -> None:
        """Test that invalid current_state is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="current_state 'INVALID' does not exist"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="INVALID",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_invalid_step_status_key(self) -> None:
        """Test that invalid step_status key is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="step_status key 'invalid_step' does not reference"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(
                    entries=(StepStatusEntry(step_id=StepId("invalid_step"), status=StepStatus.PENDING),)
                ),
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_empty_correlation_id(self) -> None:
        """Test that empty correlation_id is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="correlation_id cannot be empty"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="",
                idempotency_keys=frozenset(),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_invalid_idempotency_keys_type(self) -> None:
        """Test that invalid idempotency_keys type is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="idempotency_keys must be a frozenset"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys={"key-1", "key-2"},  # type: ignore[arg-type]
                created_at=now,
                updated_at=now,
            )

    def test_validate_idempotency_keys_happy_path(self) -> None:
        """Test idempotency keys validator accepts valid keys."""
        CeremonyInstance._validate_idempotency_keys(frozenset(["key-1", "key-2"]))

    def test_validate_idempotency_keys_rejects_invalid_type(self) -> None:
        """Test idempotency keys validator rejects invalid type."""
        with pytest.raises(ValueError, match="idempotency_keys must be a frozenset"):
            CeremonyInstance._validate_idempotency_keys({"key-1"})  # type: ignore[arg-type]

    def test_ceremony_instance_rejects_non_string_idempotency_key(self) -> None:
        """Test that non-string idempotency key is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="idempotency_keys must contain only strings"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(["key-1", 123]),  # type: ignore[arg-type]
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_empty_idempotency_key(self) -> None:
        """Test that empty idempotency key is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="idempotency_keys cannot contain empty values"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(["", "key-2"]),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_whitespace_idempotency_key(self) -> None:
        """Test that whitespace idempotency key is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="idempotency_keys cannot contain empty values"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(["   ", "key-2"]),
                created_at=now,
                updated_at=now,
            )

    def test_ceremony_instance_rejects_created_at_after_updated_at(self) -> None:
        """Test that created_at > updated_at is rejected."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        later = datetime.now(UTC)

        with pytest.raises(ValueError, match="created_at must be <= updated_at"):
            CeremonyInstance(
                instance_id="instance-123",
                definition=definition,
                current_state="STARTED",
                step_status=StepStatusMap(entries=()),
                correlation_id="corr-123",
                idempotency_keys=frozenset(),
                created_at=later,
                updated_at=now,
            )

    def test_ceremony_instance_is_terminal(self) -> None:
        """Test is_terminal method."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance_started = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )
        assert instance_started.is_terminal() is False

        instance_completed = CeremonyInstance(
            instance_id="instance-456",
            definition=definition,
            current_state="COMPLETED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-456",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )
        assert instance_completed.is_terminal() is True

    def test_ceremony_instance_is_completed(self) -> None:
        """Test is_completed method."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance_pending = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.PENDING),)
            ),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )
        assert instance_pending.is_completed() is False

        instance_completed = CeremonyInstance(
            instance_id="instance-456",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.COMPLETED),)
            ),
            correlation_id="corr-456",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )
        assert instance_completed.is_completed() is True

    def test_ceremony_instance_get_step_status(self) -> None:
        """Test get_step_status method."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.COMPLETED),)
            ),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        assert instance.get_step_status(StepId("process")) == StepStatus.COMPLETED

    def test_ceremony_instance_get_step_status_returns_pending_if_not_found(self) -> None:
        """Test that get_step_status returns PENDING for steps not in step_status."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),  # Empty, step not tracked yet
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        assert instance.get_step_status(StepId("process")) == StepStatus.PENDING

    def test_ceremony_instance_get_step_status_rejects_invalid_step_id(self) -> None:
        """Test that get_step_status rejects invalid step_id."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="step_id 'invalid_step' does not exist"):
            instance.get_step_status(StepId("invalid_step"))

    def test_ceremony_instance_has_step_in_state(self) -> None:
        """Test has_step_in_state method."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId("process"), status=StepStatus.COMPLETED),)
            ),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        assert instance.has_step_in_state(StepId("process"), StepStatus.COMPLETED) is True
        assert instance.has_step_in_state(StepId("process"), StepStatus.PENDING) is False

    def test_ceremony_instance_ensure_step_in_state(self) -> None:
        """Test ensure_step_in_state validates required state."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        step = definition.steps[0]

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        instance.ensure_step_in_state(step)

        invalid_instance = CeremonyInstance(
            instance_id="instance-456",
            definition=definition,
            current_state="COMPLETED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-456",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="requires state"):
            invalid_instance.ensure_step_in_state(step)

    def test_ceremony_instance_immutable(self) -> None:
        """Test that CeremonyInstance is immutable."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(Exception):  # Frozen dataclass raises exception
            instance.current_state = "COMPLETED"  # type: ignore[misc]

    def test_ceremony_instance_apply_transition_happy_path(self) -> None:
        """Test apply_transition updates current_state."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        transition = definition.transitions[0]

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        updated = instance.apply_transition(transition)

        assert updated.current_state == "COMPLETED"
        assert updated.updated_at >= instance.updated_at

    def test_ceremony_instance_apply_transition_rejects_invalid_state(self) -> None:
        """Test apply_transition rejects invalid from_state."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        transition = definition.transitions[0]

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="COMPLETED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            instance.apply_transition(transition)

    def test_ceremony_instance_apply_transition_rejects_terminal_state(self) -> None:
        """Test apply_transition rejects terminal instances."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        transition = definition.transitions[0]

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="COMPLETED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            instance.apply_transition(transition)

    def test_ceremony_instance_ensure_transition_executable(self) -> None:
        """Test ensure_transition_executable validates transitions."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        transition = definition.transitions[0]

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        instance.ensure_transition_executable(transition)

        invalid_instance = CeremonyInstance(
            instance_id="instance-456",
            definition=definition,
            current_state="COMPLETED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-456",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            invalid_instance.ensure_transition_executable(transition)

    def test_ceremony_instance_apply_step_result_happy_path(self) -> None:
        """Test apply_step_result updates step_status."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        result = StepResult(
            status=StepStatus.COMPLETED, output={"value": "ok"}, error_message=None
        )

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        updated = instance.apply_step_result(StepId("process"), result)

        assert updated.get_step_status(StepId("process")) == StepStatus.COMPLETED
        assert updated.get_step_output(StepId("process")) == {"value": "ok"}
        assert updated.updated_at >= instance.updated_at

    def test_ceremony_instance_apply_step_result_rejects_unknown_step(self) -> None:
        """Test apply_step_result rejects unknown step_id."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)
        result = StepResult(status=StepStatus.COMPLETED, output={}, error_message=None)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="step_id 'missing' does not exist"):
            instance.apply_step_result(StepId("missing"), result)

    def test_ceremony_instance_available_transitions(self) -> None:
        """Test available_transitions returns transitions from current state."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        transitions = instance.available_transitions()

        assert len(transitions) == 1
        assert transitions[0].from_state == "STARTED"

    def test_ceremony_instance_find_transition_by_trigger(self) -> None:
        """Test find_transition_by_trigger returns matching transition."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        transition = instance.find_transition_by_trigger(TransitionTrigger("complete"))

        assert transition.to_state == "COMPLETED"

    def test_ceremony_instance_find_transition_by_trigger_not_found(self) -> None:
        """Test find_transition_by_trigger raises when not found."""
        definition = create_minimal_definition()
        now = datetime.now(UTC)

        instance = CeremonyInstance(
            instance_id="instance-123",
            definition=definition,
            current_state="STARTED",
            step_status=StepStatusMap(entries=()),
            correlation_id="corr-123",
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Transition with trigger"):
            instance.find_transition_by_trigger(TransitionTrigger("missing"))
