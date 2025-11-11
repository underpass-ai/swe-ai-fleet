"""Role value object for Planning Service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    """Value Object for agent/user role.

    Domain Invariant: Role cannot be empty.
    Following DDD: No primitives - everything is a value object.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate Role (fail-fast).

        Raises:
            ValueError: If role is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("Role cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

