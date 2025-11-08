"""PlanningEvent domain entity - Represents an event in the planning process."""

from dataclasses import dataclass

from .entity_ids.actor_id import ActorId


@dataclass(frozen=True)
class PlanningEvent:
    """Domain entity for planning events (formerly PlanningEventDTO).

    Represents an event that occurred during the planning process,
    such as story creation, refinement, scoring, etc.

    Moved from core/reports/dtos/dtos.py to proper domain layer.
    """

    id: str
    event: str  # Event type (e.g., "story_created", "plan_drafted", "refinement_applied")
    actor_id: ActorId
    payload: dict[str, str]  # Event-specific data (immutable dict via frozen dataclass)
    ts_ms: int  # Timestamp in milliseconds

    def __post_init__(self) -> None:
        """Validate planning event."""
        if not self.id or not self.id.strip():
            raise ValueError("Planning event ID cannot be empty")
        if not self.event or not self.event.strip():
            raise ValueError("Event type cannot be empty")
        if self.ts_ms < 0:
            raise ValueError("Timestamp cannot be negative")

    def get_actor_id(self) -> str:
        """Get actor ID as string.

        Returns:
            Actor ID string
        """
        return self.actor_id.to_string()

