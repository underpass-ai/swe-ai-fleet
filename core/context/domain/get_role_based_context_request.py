"""GetRoleBasedContextRequest - Request DTO for RBAC L3 context retrieval."""

from dataclasses import dataclass

from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class GetRoleBasedContextRequest:
    """Request DTO for role-based context retrieval with RBAC L3.

    This DTO encapsulates all information needed to fetch and filter
    context data according to role-based access control policies.

    DDD-compliant: Uses domain types (StoryId, Role) instead of primitives.
    Immutable by design (frozen=True).
    """

    story_id: StoryId
    requesting_role: Role
    user_id: str  # User/agent identifier for assigned filtering

    # Optional filters
    include_timeline: bool = True
    include_summaries: bool = True
    timeline_events: int = 50  # How many timeline events to include
    max_decisions: int = 50
    max_tasks: int = 100

    def __post_init__(self) -> None:
        """Validate request.

        Raises:
            ValueError: If validation fails
        """
        if not self.user_id:
            raise ValueError("user_id is required for access control and audit logging")

        if self.timeline_events < 0:
            raise ValueError(f"timeline_events must be >= 0, got {self.timeline_events}")

        if self.max_decisions < 0:
            raise ValueError(f"max_decisions must be >= 0, got {self.max_decisions}")

        if self.max_tasks < 0:
            raise ValueError(f"max_tasks must be >= 0, got {self.max_tasks}")

    def is_for_human_role(self) -> bool:
        """Check if request is for a human role (not agent).

        Returns:
            True if requesting_role is a human role
        """
        return self.requesting_role.is_human()

    def is_for_agent_role(self) -> bool:
        """Check if request is for an agent role.

        Returns:
            True if requesting_role is an agent role
        """
        return self.requesting_role.is_agent()

    def requires_full_context(self) -> bool:
        """Check if role requires full context access.

        Returns:
            True if role needs complete context (PO, Orchestrator)
        """
        return self.requesting_role.has_full_context_access()

