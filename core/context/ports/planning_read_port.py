from typing import Any, Protocol

from core.context.domain.plan_version import PlanVersion
from core.context.domain.planning_event import PlanningEvent

# Use domain entities from Context bounded context
from core.context.domain.story_spec import StorySpec


class PlanningReadPort(Protocol):
    """Port for reading planning data (Story specs, plans, events).

    This port defines the interface for retrieving planning information
    from the persistence layer (Redis/Valkey).
    """

    def get_case_spec(self, case_id: str) -> StorySpec | None:
        """Get story specification (formerly case spec).

        Args:
            case_id: Story identifier (legacy parameter name)

        Returns:
            StorySpec domain entity or None if not found
        """
        ...

    def get_plan_draft(self, case_id: str) -> PlanVersion | None:
        """Get draft plan for story.

        Args:
            case_id: Story identifier (legacy parameter name)

        Returns:
            PlanVersion domain entity or None if not found
        """
        ...

    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEvent]:
        """Get planning events for story.

        Args:
            case_id: Story identifier (legacy parameter name)
            count: Max number of events to return

        Returns:
            List of PlanningEvent domain entities
        """
        ...

    def read_last_summary(self, case_id: str, role: str | None = None) -> str | None:
        """Read last summary for a story.

        Args:
            case_id: Story identifier (legacy parameter name)
            role: Optional role for RBAC L3 cache isolation

        Returns:
            Last summary text or None if not found
        """
        ...

    # Optional: store handoff bundle for debugging/traceability
    def save_handoff_bundle(
        self,
        case_id: str,
        bundle: dict[str, Any],
        ttl_seconds: int,
        role: str | None = None,
    ) -> None:
        """Save rehydration bundle for debugging with role isolation.

        Args:
            case_id: Story identifier (legacy parameter name)
            bundle: Serialized rehydration bundle
            ttl_seconds: Time to live in seconds
            role: Optional role for RBAC L3 cache isolation

        RBAC L3: When role is provided, implementations should include
        role in cache key to prevent cache poisoning across roles.
        """
        ...
