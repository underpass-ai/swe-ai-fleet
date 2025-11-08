from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.story_id import StoryId
from .value_objects.acceptance_criteria import AcceptanceCriteria
from .value_objects.story_tags import StoryTags
from .value_objects.story_constraints import StoryConstraints


@dataclass(frozen=True)
class StoryHeader:
    """Header information for a Story.

    Formerly known as CaseHeader (renamed for consistency with Planning Service).

    This is a pure domain value object with NO serialization methods.
    Use StoryHeaderMapper in infrastructure layer for conversions.

    All fields use Value Objects for type safety and domain-driven design.
    """

    story_id: StoryId
    title: str
    constraints: StoryConstraints
    acceptance_criteria: AcceptanceCriteria
    tags: StoryTags

    def __post_init__(self) -> None:
        """Validate story header."""
        if not self.title or not self.title.strip():
            raise ValueError("Story title cannot be empty")

