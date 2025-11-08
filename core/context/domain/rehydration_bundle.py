from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.story_id import StoryId
from .role import Role
from .role_context_fields import RoleContextFields
from .value_objects.rehydration_stats import RehydrationStats


@dataclass(frozen=True)
class RehydrationBundle:
    """Bundle containing rehydrated context for multiple roles.

    This aggregate holds context data for a Story, organized by role.
    Each role gets a filtered view (RoleContextFields) based on their needs.

    This is a pure domain aggregate with NO serialization methods.
    Use RehydrationBundleMapper in infrastructure layer for conversions.
    """

    story_id: StoryId
    generated_at_ms: int
    packs: dict[Role, RoleContextFields]  # Role -> RoleContextFields
    stats: RehydrationStats

    def __post_init__(self) -> None:
        """Validate bundle."""
        if self.generated_at_ms < 0:
            raise ValueError("generated_at_ms cannot be negative")
        if not self.packs:
            raise ValueError("RehydrationBundle must contain at least one role pack")

    def get_pack_for_role(self, role: Role) -> RoleContextFields:
        """Get context pack for a specific role.

        Args:
            role: Role enum

        Returns:
            RoleContextFields for the role

        Raises:
            KeyError: If role not found in bundle
        """
        if role not in self.packs:
            raise KeyError(f"Role '{role.value}' not found in rehydration bundle")
        return self.packs[role]

    def has_role(self, role: Role) -> bool:
        """Check if bundle contains pack for role.

        Args:
            role: Role enum

        Returns:
            True if role exists in bundle
        """
        return role in self.packs

    def get_roles(self) -> list[Role]:
        """Get list of roles in this bundle.

        Returns:
            List of Role enums
        """
        return list(self.packs.keys())
