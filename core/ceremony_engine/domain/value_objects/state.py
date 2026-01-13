"""State: Value Object representing a ceremony state."""

from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    """
    Value Object: Ceremony state.

    Domain Invariants:
    - id must be non-empty, UPPERCASE (e.g., "INITIALIZED")
    - description must be non-empty
    - terminal and initial are boolean flags
    - Immutable (frozen=True)

    Business Rules:
    - States define the lifecycle stages of a ceremony
    - Only one state can be initial (validated at CeremonyDefinition level)
    - Terminal states cannot have outgoing transitions (validated at CeremonyDefinition level)
    """

    id: str  # UPPERCASE identifier
    description: str
    terminal: bool = False
    initial: bool = False

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If state is invalid
        """
        if not self.id or not self.id.strip():
            raise ValueError("State id cannot be empty")

        if self.id != self.id.upper():
            raise ValueError(f"State id must be UPPERCASE: {self.id}")

        if not self.description or not self.description.strip():
            raise ValueError("State description cannot be empty")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.id
