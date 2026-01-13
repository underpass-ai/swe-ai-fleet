"""Guard: Value Object representing a guard condition."""

from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects.guard_type import GuardType


@dataclass(frozen=True)
class Guard:
    """
    Value Object: Guard condition.

    Domain Invariants:
    - name must be non-empty
    - type must be AUTOMATED or HUMAN
    - check must be non-empty for AUTOMATED guards
    - role is optional but recommended for HUMAN guards
    - threshold is optional (for numeric guards)
    - Immutable (frozen=True)

    Business Rules:
    - Guards define conditions that must be satisfied for transitions
    - AUTOMATED guards are evaluated programmatically
    - HUMAN guards require human decision/approval
    """

    name: str
    type: GuardType
    check: str  # Expression/description
    role: str | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If guard is invalid
        """
        if not self.name or not self.name.strip():
            raise ValueError("Guard name cannot be empty")

        if not self.check or not self.check.strip():
            raise ValueError("Guard check cannot be empty")

        if self.type == GuardType.AUTOMATED and not self.check.strip():
            # check is required for automated guards (already validated above, but explicit)
            pass
