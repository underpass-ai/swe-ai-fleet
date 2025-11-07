"""Data Transfer Object for Planning Service events.

DTOs represent external system contracts (Planning Service).
Following DDD + Hexagonal Architecture principles.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningStoryTransitionedDTO:
    """DTO for planning.story.transitioned event.

    Contract with Planning Service (external bounded context).
    Represents story state transition from Planning Service.

    Fields match Planning Service event schema:
    {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": ["task-001", "task-002"],
        "timestamp": "2025-11-06T10:30:00Z"
    }

    Following DDD:
    - DTO does NOT implement to_dict() / from_dict()
    - Conversion handled by mapper in infrastructure layer
    - Immutable (frozen=True)
    - Fail-fast validation

    Domain Invariants:
    - story_id cannot be empty
    - to_state cannot be empty
    - tasks must be a list (can be empty)
    - timestamp must be valid ISO format
    """

    story_id: str
    from_state: str
    to_state: str
    tasks: list[str]
    timestamp: str

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.story_id:
            raise ValueError("story_id cannot be empty")

        if not self.to_state:
            raise ValueError("to_state cannot be empty")

        if not isinstance(self.tasks, list):
            raise ValueError(f"tasks must be a list, got {type(self.tasks)}")

        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")

