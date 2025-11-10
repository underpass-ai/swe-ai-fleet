"""Mapper for Story entity - Infrastructure layer.

Handles conversion between external formats (dict/JSON) and Story domain entity.
"""

from typing import Any

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story import Story
from core.context.domain.story_spec import StorySpec


class StoryMapper:
    """Mapper for Story entity conversions."""

    @staticmethod
    def from_spec(spec: StorySpec) -> Story:
        """Create Story entity from StorySpec.

        Args:
            spec: StorySpec domain entity

        Returns:
            Story domain entity

        Raises:
            ValueError: If epic_id is missing (domain invariant)
        """
        # StorySpec should include epic_id
        # If not present, this will raise ValueError from Story.__post_init__
        epic_id = getattr(spec, "epic_id", None)
        if not epic_id:
            raise ValueError(
                f"StorySpec for {spec.story_id} missing epic_id. "
                "Domain Invariant: Story MUST belong to an Epic."
            )

        return Story(
            story_id=spec.story_id,
            epic_id=epic_id,
            name=spec.title,
        )

    @staticmethod
    def from_event_payload(payload: dict[str, Any]) -> Story:
        """Create a Story from event payload data.

        Args:
            payload: Event payload dict with story_id, epic_id, and optional name

        Returns:
            Story domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If story_id or epic_id is invalid
        """
        return Story(
            story_id=StoryId(value=payload["story_id"]),
            epic_id=EpicId(value=payload["epic_id"]),  # REQUIRED
            name=payload.get("name", ""),
        )

    @staticmethod
    def to_graph_properties(story: Story) -> dict[str, Any]:
        """Convert Story to properties suitable for Neo4j graph storage.

        Args:
            story: Story domain entity

        Returns:
            Dictionary with properties for Neo4j (includes epic_id for hierarchy)
        """
        return {
            "story_id": story.story_id.to_string(),  # Explicit conversion using Tell, Don't Ask
            "epic_id": story.epic_id.to_string(),  # Parent reference for hierarchy
            "name": story.name,
        }

