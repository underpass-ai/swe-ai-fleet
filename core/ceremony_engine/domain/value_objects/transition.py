"""Transition: Value Object representing a state transition."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Transition:
    """
    Value Object: State transition.

    Domain Invariants:
    - from_state must be non-empty (references a State id)
    - to_state must be non-empty (references a State id)
    - trigger must be non-empty
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
    trigger: str
    guards: tuple[str, ...]
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

        if not self.trigger or not self.trigger.strip():
            raise ValueError("Transition trigger cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Transition description cannot be empty")

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.from_state} -> {self.to_state} ({self.trigger})"
