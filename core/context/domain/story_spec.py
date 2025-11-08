"""StorySpec domain entity - Complete specification of a story."""

from dataclasses import dataclass

from .entity_ids.actor_id import ActorId
from .entity_ids.story_id import StoryId
from .value_objects.acceptance_criteria import AcceptanceCriteria
from .value_objects.story_constraints import StoryConstraints
from .value_objects.story_tags import StoryTags


@dataclass(frozen=True)
class StorySpec:
    """Complete specification of a Story (formerly CaseSpecDTO).

    This is a rich domain entity that represents all the information
    needed to understand and implement a user story.

    Moved from core/reports/dtos/dtos.py to proper domain layer.
    """

    story_id: StoryId
    title: str
    description: str
    acceptance_criteria: AcceptanceCriteria
    constraints: StoryConstraints
    requester_id: ActorId
    tags: StoryTags
    created_at_ms: int

    def __post_init__(self) -> None:
        """Validate story spec."""
        if not self.title or not self.title.strip():
            raise ValueError("Story title cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Story description cannot be empty")
        if self.created_at_ms < 0:
            raise ValueError("created_at_ms cannot be negative")

