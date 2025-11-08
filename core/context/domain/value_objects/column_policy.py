"""ColumnPolicy Value Object - RBAC L3 column-level security policy."""

from dataclasses import dataclass

from core.context.domain.entity_type import EntityType
from core.context.domain.role import Role


@dataclass(frozen=True)
class ColumnPolicy:
    """Policy defining which columns a role can access for an entity type.

    RBAC L3: Column-level security (whitelist-based).

    Domain Invariants:
    - entity_type must be valid EntityType
    - allowed_columns cannot be empty
    - allowed_columns must be valid for the entity_type

    Example:
        developer_story_policy = ColumnPolicy(
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
            allowed_columns=("title", "status", "assigned_to"),
        )
    """

    entity_type: EntityType
    role: Role
    allowed_columns: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate column policy (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.allowed_columns:
            raise ValueError(
                f"allowed_columns cannot be empty for {self.entity_type.value}. "
                f"At least one column must be whitelisted."
            )

        # Validate all columns are valid for this entity type
        valid_columns = EntityType.get_valid_columns(self.entity_type)

        for col in self.allowed_columns:
            if not col or not col.strip():
                raise ValueError(
                    f"Column name cannot be empty in policy for {self.entity_type.value}"
                )

            if col not in valid_columns:
                raise ValueError(
                    f"Invalid column '{col}' for entity type {self.entity_type.value}. "
                    f"Valid columns: {valid_columns}"
                )

    def allows_column(self, column_name: str) -> bool:
        """Check if column is allowed for this role.

        Args:
            column_name: Column to check

        Returns:
            True if column is in whitelist
        """
        return column_name in self.allowed_columns

