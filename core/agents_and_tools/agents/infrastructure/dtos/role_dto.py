"""DTO for Role in RBAC system."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleDTO:
    """DTO for Role.

    Represents role information for serialization/deserialization.
    Following cursorrules, this is a simple DTO with no serialization methods.

    Conversion to/from domain entity is handled by RoleMapper in infrastructure layer.

    Attributes:
        name: Role name (e.g., "architect", "qa", "developer")
        scope: Role scope (e.g., "technical", "business", "quality")
        allowed_actions: List of action names allowed for this role
    """

    name: str
    scope: str
    allowed_actions: list[str]

    def __post_init__(self) -> None:
        """Validate DTO invariants (fail-fast).

        Raises:
            ValueError: If name is empty
            ValueError: If scope is empty
            ValueError: If allowed_actions is empty
        """
        if not self.name:
            raise ValueError("Role name cannot be empty")
        if not self.scope:
            raise ValueError("Role scope cannot be empty")
        if not self.allowed_actions:
            raise ValueError("allowed_actions cannot be empty")

