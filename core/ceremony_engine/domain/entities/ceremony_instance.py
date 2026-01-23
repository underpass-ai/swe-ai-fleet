"""CeremonyInstance: Domain entity representing a ceremony execution instance."""

from dataclasses import dataclass, field
from datetime import datetime

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_output_map import StepOutputMap
from core.ceremony_engine.domain.value_objects.step_status_map import StepStatusMap
from core.ceremony_engine.domain.value_objects.transition import Transition
from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger


@dataclass(frozen=True)
class CeremonyInstance:
    """
    Domain Entity: Ceremony execution instance.

    Represents the runtime state of a ceremony being executed.
    This is the aggregate root for ceremony execution state.

    Domain Invariants:
    - instance_id must be non-empty (UUID format recommended)
    - definition must be a valid CeremonyDefinition
    - current_state must reference an existing state in definition
    - step_status keys must reference existing steps in definition
    - correlation_id must be non-empty (for distributed tracing)
    - idempotency_keys must be a set (can be empty)
    - created_at <= updated_at
    - Immutable (frozen=True)

    Business Rules:
    - Instances are created from CeremonyDefinition
    - State transitions follow definition's transitions
    - Step status tracks execution progress
    - Idempotency keys prevent duplicate operations
    - Correlation ID enables end-to-end tracing
    """

    instance_id: str
    definition: CeremonyDefinition
    current_state: str
    step_status: StepStatusMap  # step_id -> status
    correlation_id: str
    idempotency_keys: frozenset[str]
    created_at: datetime
    updated_at: datetime
    step_outputs: StepOutputMap = field(
        default_factory=lambda: StepOutputMap(entries=())
    )  # step_id -> output

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.instance_id or not self.instance_id.strip():
            raise ValueError("instance_id cannot be empty")

        if not isinstance(self.definition, CeremonyDefinition):
            raise ValueError(
                f"definition must be a CeremonyDefinition, got {type(self.definition)}"
            )

        if not isinstance(self.step_status, StepStatusMap):
            raise ValueError(
                f"step_status must be a StepStatusMap, got {type(self.step_status)}"
            )
        if not isinstance(self.step_outputs, StepOutputMap):
            raise ValueError(
                f"step_outputs must be a StepOutputMap, got {type(self.step_outputs)}"
            )

        # Validate current_state references existing state
        state_ids = {state.id for state in self.definition.states}
        if self.current_state not in state_ids:
            raise ValueError(
                f"current_state '{self.current_state}' does not exist in definition"
            )

        # Validate step_status keys reference existing steps
        step_ids = {step.id for step in self.definition.steps}
        for entry in self.step_status.entries:
            if entry.step_id not in step_ids:
                raise ValueError(
                    f"step_status key '{entry.step_id.value}' does not reference an existing step"
                )
        for entry in self.step_outputs.entries:
            if entry.step_id not in step_ids:
                raise ValueError(
                    f"step_outputs key '{entry.step_id.value}' does not reference an existing step"
                )

        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("correlation_id cannot be empty")

        self._validate_idempotency_keys(self.idempotency_keys)

        if self.created_at > self.updated_at:
            raise ValueError("created_at must be <= updated_at")

    @staticmethod
    def _validate_idempotency_keys(idempotency_keys: frozenset[object]) -> None:
        """Validate idempotency keys are non-empty strings."""
        if not isinstance(idempotency_keys, frozenset):
            raise ValueError(
                f"idempotency_keys must be a frozenset, got {type(idempotency_keys)}"
            )
        for key in idempotency_keys:
            if not isinstance(key, str):
                raise ValueError(
                    f"idempotency_keys must contain only strings, got {type(key)}"
                )
            if not key.strip():
                raise ValueError("idempotency_keys cannot contain empty values")

    def is_terminal(self) -> bool:
        """Check if ceremony instance is in a terminal state.

        Returns:
            True if current_state is terminal
        """
        current_state_obj = self.definition.get_state_by_id(self.current_state)
        return current_state_obj is not None and current_state_obj.terminal

    def is_completed(self) -> bool:
        """Check if all steps are completed.

        Returns:
            True if all steps have COMPLETED status
        """
        if not self.definition.steps:
            return True

        return all(
            self.step_status.get(step.id, StepStatus.PENDING) == StepStatus.COMPLETED
            for step in self.definition.steps
        )

    def get_step_status(self, step_id: StepId) -> StepStatus:
        """Get status of a specific step.

        Args:
            step_id: Step ID to lookup

        Returns:
            StepStatus (PENDING if step not found in step_status)

        Raises:
            ValueError: If step_id does not exist in definition
        """
        step_ids = {step.id for step in self.definition.steps}
        if step_id not in step_ids:
            raise ValueError(f"step_id '{step_id.value}' does not exist in definition")

        return self.step_status.get(step_id, StepStatus.PENDING)

    def has_step_in_state(self, step_id: StepId, status: StepStatus) -> bool:
        """Check if a step has a specific status.

        Args:
            step_id: Step ID to check
            status: Status to check for

        Returns:
            True if step has the specified status
        """
        return self.get_step_status(step_id) == status

    def ensure_step_in_state(self, step: Step) -> None:
        """Ensure the instance is in the correct state for a step.

        Args:
            step: Step to validate

        Raises:
            ValueError: If instance is not in the step's required state
        """
        if self.current_state != step.state:
            raise ValueError(
                f"Step '{step.id.value}' requires state '{step.state}', "
                f"but instance is in state '{self.current_state}'"
            )

    def apply_step_result(self, step_id: StepId, result: StepResult) -> "CeremonyInstance":
        """Apply a step result to this instance.

        Args:
            step_id: Step ID that was executed
            result: Step execution result

        Returns:
            New CeremonyInstance with updated step status

        Raises:
            ValueError: If step_id does not exist in definition
        """
        step_ids = {step.id for step in self.definition.steps}
        if step_id not in step_ids:
            raise ValueError(f"step_id '{step_id.value}' does not exist in definition")

        from datetime import UTC, datetime

        updated_step_status = self.step_status.with_status(step_id, result.status)
        updated_step_outputs = self.step_outputs.with_output(step_id, result.output)

        return (
            self.to_builder()
            .with_step_status(updated_step_status)
            .with_step_outputs(updated_step_outputs)
            .with_updated_at(datetime.now(UTC))
            .build()
        )

    def available_transitions(self) -> tuple[Transition, ...]:
        """Return transitions available from the current state."""
        return tuple(
            transition
            for transition in self.definition.transitions
            if transition.from_state == self.current_state
        )

    def find_transition_by_trigger(self, trigger: TransitionTrigger) -> Transition:
        """Find a transition by trigger from the current state.

        Args:
            trigger: Transition trigger

        Returns:
            Transition if found

        Raises:
            ValueError: If transition not found
        """
        for transition in self.definition.transitions:
            if transition.from_state == self.current_state and transition.trigger == trigger:
                return transition

        raise ValueError(
            f"Transition with trigger '{trigger.value}' not found from state '{self.current_state}'"
        )

    def apply_transition(self, transition: Transition) -> "CeremonyInstance":
        """Apply a state transition to this instance.

        Args:
            transition: Transition to apply

        Returns:
            New CeremonyInstance with updated state

        Raises:
            ValueError: If transition is invalid or instance is terminal
        """
        self.ensure_transition_executable(transition)

        from datetime import UTC, datetime

        return (
            self.to_builder()
            .with_current_state(transition.to_state)
            .with_updated_at(datetime.now(UTC))
            .build()
        )

    def get_step_output(self, step_id: StepId) -> dict[str, object] | None:
        """Get output for a step if present."""
        return self.step_outputs.get(step_id)

    def to_builder(self) -> "CeremonyInstanceBuilder":
        """Create a builder from this instance."""
        return CeremonyInstanceBuilder(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=self.current_state,
            step_status=self.step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=self.updated_at,
            step_outputs=self.step_outputs,
        )

    def ensure_transition_executable(self, transition: Transition) -> None:
        """Ensure a transition can be applied from current state.

        Args:
            transition: Transition to validate

        Raises:
            ValueError: If transition cannot be executed
        """
        if self.is_terminal():
            raise ValueError(
                f"Cannot transition from terminal state '{self.current_state}'"
            )
        if self.current_state != transition.from_state:
            raise ValueError(
                f"Transition '{transition.trigger.value}' requires state '{transition.from_state}', "
                f"but instance is in state '{self.current_state}'"
            )


@dataclass(frozen=True)
class CeremonyInstanceBuilder:
    """Builder for CeremonyInstance."""

    instance_id: str
    definition: CeremonyDefinition
    current_state: str
    step_status: StepStatusMap
    correlation_id: str
    idempotency_keys: frozenset[str]
    created_at: datetime
    updated_at: datetime
    step_outputs: StepOutputMap

    def with_current_state(self, current_state: str) -> "CeremonyInstanceBuilder":
        return CeremonyInstanceBuilder(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=current_state,
            step_status=self.step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=self.updated_at,
            step_outputs=self.step_outputs,
        )

    def with_step_status(self, step_status: StepStatusMap) -> "CeremonyInstanceBuilder":
        return CeremonyInstanceBuilder(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=self.current_state,
            step_status=step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=self.updated_at,
            step_outputs=self.step_outputs,
        )

    def with_step_outputs(self, step_outputs: StepOutputMap) -> "CeremonyInstanceBuilder":
        return CeremonyInstanceBuilder(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=self.current_state,
            step_status=self.step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=self.updated_at,
            step_outputs=step_outputs,
        )

    def with_updated_at(self, updated_at: datetime) -> "CeremonyInstanceBuilder":
        return CeremonyInstanceBuilder(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=self.current_state,
            step_status=self.step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=updated_at,
            step_outputs=self.step_outputs,
        )

    def build(self) -> CeremonyInstance:
        return CeremonyInstance(
            instance_id=self.instance_id,
            definition=self.definition,
            current_state=self.current_state,
            step_status=self.step_status,
            correlation_id=self.correlation_id,
            idempotency_keys=self.idempotency_keys,
            created_at=self.created_at,
            updated_at=self.updated_at,
            step_outputs=self.step_outputs,
        )
