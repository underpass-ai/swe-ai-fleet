"""Role value object for Planning Service."""

from __future__ import annotations

from dataclasses import dataclass

from .role_type import RoleType


@dataclass(frozen=True)
class Role:
    """Value Object for agent/user role.

    Domain Invariant: Role must be a valid RoleType.
    Following DDD: No primitives - use enum for fixed values.
    """

    value: RoleType

    def __post_init__(self) -> None:
        """Validate Role (fail-fast).

        Raises:
            ValueError: If role is invalid
        """
        if not isinstance(self.value, RoleType):
            raise ValueError(f"Role must be RoleType enum, got: {type(self.value)}")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value.value

    @classmethod
    def system(cls) -> Role:
        """Factory: Create SYSTEM role.

        Returns:
            Role for system-level operations
        """
        return cls(RoleType.SYSTEM)

    @classmethod
    def developer(cls) -> Role:
        """Factory: Create DEVELOPER role.

        Returns:
            Role for software developers
        """
        return cls(RoleType.DEVELOPER)

