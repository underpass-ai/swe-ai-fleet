"""Mapper for RehydrationBundle - Infrastructure layer."""

from typing import Any

from core.context.domain.rehydration_bundle import RehydrationBundle
from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.value_objects.rehydration_stats import RehydrationStats
from core.context.domain.role_context_fields import RoleContextFields
from core.context.infrastructure.mappers.role_context_fields_mapper import RoleContextFieldsMapper


class RehydrationBundleMapper:
    """Mapper for RehydrationBundle serialization."""

    @staticmethod
    def to_dict(bundle: RehydrationBundle) -> dict[str, Any]:
        """Convert RehydrationBundle to dictionary for persistence.

        Args:
            bundle: RehydrationBundle domain aggregate

        Returns:
            Dictionary representation suitable for Redis/Valkey
        """
        return {
            "story_id": bundle.story_id.to_string(),
            "generated_at_ms": bundle.generated_at_ms,
            "packs": {
                role.value: RoleContextFieldsMapper.to_dict(pack)
                for role, pack in bundle.packs.items()
            },
            "stats": bundle.stats.to_dict(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RehydrationBundle:
        """Create RehydrationBundle from dictionary (e.g., from Redis).

        Args:
            data: Dictionary with serialized bundle data

        Returns:
            RehydrationBundle domain aggregate

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        # Convert string keys to Role enums (fail-fast if invalid)
        packs: dict[Role, RoleContextFields] = {}
        for role_str, pack_data in data.get("packs", {}).items():
            try:
                role_enum = Role(role_str)
            except ValueError as e:
                raise ValueError(
                    f"Invalid role '{role_str}' in serialized bundle. "
                    f"Valid roles: {', '.join(r.value for r in Role)}"
                ) from e

            # Reconstruct RoleContextFields using RoleContextFieldsMapper
            packs[role_enum] = RoleContextFieldsMapper.from_dict(pack_data)

        return RehydrationBundle(
            story_id=StoryId(value=data["story_id"]),
            generated_at_ms=int(data["generated_at_ms"]),
            packs=packs,
            stats=RehydrationStats.from_dict(data["stats"]),
        )






