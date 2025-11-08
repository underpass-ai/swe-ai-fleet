"""Mapper for StorySpec entity - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story_spec import StorySpec
from core.context.domain.value_objects.acceptance_criteria import AcceptanceCriteria
from core.context.domain.value_objects.story_constraints import StoryConstraints
from core.context.domain.value_objects.story_tags import StoryTags


class StorySpecMapper:
    """Mapper for StorySpec conversions (formerly CaseSpecDTO)."""

    @staticmethod
    def from_redis_data(data: dict[str, Any]) -> StorySpec:
        """Create StorySpec from Redis/Valkey data.

        Args:
            data: Dictionary from Redis with story spec

        Returns:
            StorySpec domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        return StorySpec(
            story_id=StoryId(value=data["story_id"]),
            title=data["title"],
            description=data["description"],
            acceptance_criteria=AcceptanceCriteria.from_list(data.get("acceptance_criteria", [])),
            constraints=StoryConstraints.from_dict(data.get("constraints", {})),
            requester_id=ActorId(value=data.get("requester_id", "unknown")),
            tags=StoryTags.from_list(data.get("tags", [])),
            created_at_ms=int(data.get("created_at_ms", 0)),
        )

    @staticmethod
    def to_redis_data(spec: StorySpec) -> dict[str, Any]:
        """Convert StorySpec to Redis/Valkey storage format.

        Args:
            spec: StorySpec domain entity

        Returns:
            Dictionary for Redis storage
        """
        return {
            "story_id": spec.story_id.to_string(),
            "title": spec.title,
            "description": spec.description,
            "acceptance_criteria": spec.acceptance_criteria.to_list(),
            "constraints": spec.constraints.to_dict(),
            "requester_id": spec.requester_id.to_string(),
            "tags": spec.tags.to_list(),
            "created_at_ms": spec.created_at_ms,
        }

