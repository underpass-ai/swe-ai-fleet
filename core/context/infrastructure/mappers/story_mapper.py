"""Mapper for Story entity - Infrastructure layer.

Handles conversion between external formats (dict/JSON) and Story domain entity.
"""

from typing import Any

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
        """
        return Story(
            story_id=spec.story_id,
            name=spec.title,
        )

    @staticmethod
    def from_event_payload(payload: dict[str, Any]) -> Story:
        """Create a Story from event payload data.

        Args:
            payload: Event payload dict with story_id and optional name

        Returns:
            Story domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If story_id is invalid
        """
        return Story(
            story_id=StoryId(value=payload["story_id"]),
            name=payload.get("name", ""),
        )

    @staticmethod
    def to_graph_properties(story: Story) -> dict[str, Any]:
        """Convert Story to properties suitable for Neo4j graph storage.

        Args:
            story: Story domain entity

        Returns:
            Dictionary with properties for Neo4j
        """
        return {
            "story_id": story.story_id.to_string(),  # Explicit conversion using Tell, Don't Ask
            "name": story.name,
        }

