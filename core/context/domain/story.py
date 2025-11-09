# core/context/domain/story.py
from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.epic_id import EpicId
from .entity_ids.story_id import StoryId


@dataclass(frozen=True)
class Story:
    """Domain model representing a Story entity in the context graph.

    A Story represents a user story that needs to be completed.
    It serves as the root entity in the context graph, connecting to plans, tasks, and decisions.

    Formerly known as Case (renamed for consistency with Planning Service).

    Hierarchy: Project → Epic → Story → Task

    DOMAIN INVARIANT: Story MUST belong to an Epic.
    NO orphan stories allowed.

    This is a pure domain entity with NO serialization methods.
    Use StoryMapper in infrastructure layer for conversions.
    """

    story_id: StoryId
    epic_id: EpicId  # REQUIRED - enforces domain invariant
    name: str

    def __post_init__(self) -> None:
        """Validate story (fail-fast).

        Domain Invariants:
        - Story ID cannot be empty
        - Story name cannot be empty
        - Story MUST belong to an Epic (epic_id is REQUIRED)

        Raises:
            ValueError: If validation fails
        """
        if not self.story_id.value or not self.story_id.value.strip():
            raise ValueError("Story ID cannot be empty")

        if not self.name or not self.name.strip():
            raise ValueError("Story name cannot be empty")

        # DOMAIN INVARIANT: Story MUST have Epic
        if not self.epic_id.value or not self.epic_id.value.strip():
            raise ValueError(
                "Story MUST belong to an Epic. epic_id is REQUIRED. "
                "Domain Invariant: No orphan stories allowed. "
                "See docs/architecture/DOMAIN_INVARIANTS_BUSINESS_RULES.md"
            )

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context (Tell, Don't Ask).

        Returns:
            Dictionary with logging fields
        """
        return {
            "story_id": self.story_id.to_string(),
            "epic_id": self.epic_id.to_string(),
            "name": self.name,
        }

