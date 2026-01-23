"""Transition: Value Object representing a state transition."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.ceremony_engine.domain.value_objects.guard import Guard
from core.ceremony_engine.domain.value_objects.guard_name import GuardName
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger

if TYPE_CHECKING:
    from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


@dataclass(frozen=True)
class Transition:
    """
    Value Object: State transition.

    Domain Invariants:
    - from_state must be non-empty (references a State id)
    - to_state must be non-empty (references a State id)
    - trigger must be a TransitionTrigger
    - guards is a tuple of guard names (referenced guards validated at CeremonyDefinition level)
    - description must be non-empty
    - Immutable (frozen=True)

    Business Rules:
    - Transitions define how ceremonies move between states
    - Guards must be satisfied for the transition to occur
    - from_state and to_state must reference existing states (validated at CeremonyDefinition level)
    - trigger must be unique per from_state (validated at CeremonyDefinition level)
    """

    from_state: str  # State ID
    to_state: str  # State ID
    trigger: TransitionTrigger
    guards: tuple[GuardName, ...]
    description: str

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If transition is invalid
        """
        if not self.from_state or not self.from_state.strip():
            raise ValueError("Transition from_state cannot be empty")

        if not self.to_state or not self.to_state.strip():
            raise ValueError("Transition to_state cannot be empty")

        if not isinstance(self.trigger, TransitionTrigger):
            raise ValueError(
                f"Transition trigger must be a TransitionTrigger, got {type(self.trigger)}"
            )

        if not self.description or not self.description.strip():
            raise ValueError("Transition description cannot be empty")

        for guard_name in self.guards:
            if not isinstance(guard_name, GuardName):
                raise ValueError(
                    f"Transition guard must be GuardName, got {type(guard_name)}"
                )

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.from_state} -> {self.to_state} ({self.trigger.value})"

    def evaluate_guards(
        self,
        instance: "CeremonyInstance",
        context: ExecutionContext,
        guards: Mapping[str, Guard],
    ) -> bool:
        """Evaluate all guards for this transition.

        Args:
            instance: Ceremony instance
            context: Execution context
            guards: Guard registry by name

        Returns:
            True if all guards pass, False otherwise

        Raises:
            ValueError: If a referenced guard is missing
        """
        if not self.guards:
            return True

        for guard_name in self.guards:
            guard = guards.get(guard_name)
            if not guard:
                raise ValueError(f"Guard '{guard_name.value}' not found in definition")
            if not guard.evaluate(instance, context):
                return False

        return True
