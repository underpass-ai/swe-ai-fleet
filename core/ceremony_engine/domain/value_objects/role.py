"""Role: Value Object representing a role with allowed actions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    """
    Value Object: Role with allowed actions.

    Domain Invariants:
    - id must be non-empty, UPPERCASE (e.g., "PO", "SYSTEM")
    - description must be non-empty
    - allowed_actions is a tuple of action identifiers (steps or triggers)
    - Immutable (frozen=True)

    Business Rules:
    - Roles define who can perform which actions
    - allowed_actions reference steps or triggers (validated at CeremonyDefinition level)
    """

    id: str  # UPPERCASE identifier
    description: str
    allowed_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If role is invalid
        """
        if not self.id or not self.id.strip():
            raise ValueError("Role id cannot be empty")

        if self.id != self.id.upper():
            raise ValueError(f"Role id must be UPPERCASE: {self.id}")

        if not self.description or not self.description.strip():
            raise ValueError("Role description cannot be empty")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.id
