"""ColumnFilterService - Domain service for column-level security (RBAC L3)."""

from dataclasses import dataclass, fields
from typing import Any

from core.context.domain.role import Role
from core.context.domain.entity_type import EntityType
from core.context.domain.value_objects.column_policy import ColumnPolicy


@dataclass
class ColumnFilterService:
    """Domain service for filtering entity columns based on role.

    RBAC L3: Column-level security (whitelist-based).

    This service applies column-level filtering to domain entities,
    removing fields that the requesting role should not see.
    """

    policies: dict[tuple[EntityType, Role], ColumnPolicy]

    def filter_entity(
        self,
        entity: Any,
        entity_type: EntityType,
        role: Role,
    ) -> Any:
        """Filter entity columns based on role policy.

        Args:
            entity: Entity to filter (domain entity or dict)
            entity_type: Type of entity
            role: Role requesting access

        Returns:
            Filtered entity (same type as input)

        Raises:
            ValueError: If no policy exists for (entity_type, role)
        """
        # Get policy for this entity type and role
        policy_key = (entity_type, role)

        if policy_key not in self.policies:
            raise ValueError(
                f"No column policy defined for entity_type={entity_type.value}, role={role.value}. "
                f"Available policies: {list(self.policies.keys())}"
            )

        policy = self.policies[policy_key]

        # If entity is a dict, filter directly
        if isinstance(entity, dict):
            return self._filter_dict(entity, policy)

        # If entity is a dataclass, convert to dict, filter, and reconstruct
        if hasattr(entity, "__dataclass_fields__"):
            entity_dict = self._dataclass_to_dict(entity)
            filtered_dict = self._filter_dict(entity_dict, policy)
            return self._dict_to_dataclass(filtered_dict, type(entity))

        # For other types, return as-is (no filtering)
        # This handles primitives, tuples, etc.
        return entity

    def _filter_dict(
        self,
        entity_data: dict[str, Any],
        policy: ColumnPolicy,
    ) -> dict[str, Any]:
        """Filter dictionary based on policy.

        Args:
            entity_data: Dictionary to filter
            policy: Column policy to apply

        Returns:
            Filtered dictionary with only whitelisted columns
        """
        return {
            key: value
            for key, value in entity_data.items()
            if policy.allows_column(key)
        }

    def _dataclass_to_dict(self, entity: Any) -> dict[str, Any]:
        """Convert dataclass to dict.

        Args:
            entity: Dataclass instance

        Returns:
            Dictionary representation
        """
        return {
            field.name: getattr(entity, field.name)
            for field in fields(entity)
        }

    def _dict_to_dataclass(self, data: dict[str, Any], cls: type) -> Any:
        """Convert dict back to dataclass.

        Args:
            data: Dictionary data
            cls: Dataclass type

        Returns:
            Dataclass instance

        Note:
            Only includes fields that exist in the dataclass definition.
            Extra fields in data are ignored.
        """
        # Get valid field names for this dataclass
        valid_fields = {field.name for field in fields(cls)}

        # Filter data to only include valid fields
        filtered_data = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        # Construct dataclass with filtered data
        return cls(**filtered_data)
