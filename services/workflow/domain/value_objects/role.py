"""Role value object.

Represents an agent role in the workflow system.
Following Domain-Driven Design principles.
"""

from dataclasses import dataclass


# Special value: Semantic null for role (better than empty string)
NO_ROLE = "no_role"


@dataclass(frozen=True)
class Role:
    """Role value object.

    Represents a role in the multi-agent workflow system.
    Immutable following DDD principles.

    Valid roles:
    - developer: Implements features
    - architect: Reviews technical design
    - qa: Tests and validates quality
    - po: Product Owner, approves business value
    - system: System-initiated actions
    """

    value: str

    # Valid role identifiers
    VALID_ROLES = frozenset({"developer", "architect", "qa", "po", "system"})

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type validation is handled by type hints.
        """
        if not self.value:
            raise ValueError("Role cannot be empty")

        # Business rule: only specific roles are valid
        normalized = self.value.lower()
        if normalized not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role: {self.value}. "
                f"Valid roles: {', '.join(sorted(self.VALID_ROLES))}"
            )

    def is_validator(self) -> bool:
        """Check if this role performs validation/review."""
        return self.value.lower() in ("architect", "qa", "po")

    def is_implementer(self) -> bool:
        """Check if this role implements features."""
        return self.value.lower() == "developer"

    def is_system(self) -> bool:
        """Check if this is a system role."""
        return self.value.lower() == "system"

    def __str__(self) -> str:
        """String representation."""
        return self.value.lower()

    def __eq__(self, other: object) -> bool:
        """Equality comparison (case-insensitive)."""
        if not isinstance(other, Role):
            return False
        return self.value.lower() == other.value.lower()

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.value.lower())

    @classmethod
    def developer(cls) -> "Role":
        """Factory: Developer role."""
        return cls("developer")

    @classmethod
    def architect(cls) -> "Role":
        """Factory: Architect role."""
        return cls("architect")

    @classmethod
    def qa(cls) -> "Role":
        """Factory: QA role."""
        return cls("qa")

    @classmethod
    def po(cls) -> "Role":
        """Factory: Product Owner role."""
        return cls("po")

    @classmethod
    def system(cls) -> "Role":
        """Factory: System role."""
        return cls("system")

