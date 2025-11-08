"""Mapper for StoryHeader - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story_header import StoryHeader
from core.context.domain.value_objects.acceptance_criteria import AcceptanceCriteria
from core.context.domain.value_objects.story_constraints import StoryConstraints
from core.context.domain.value_objects.story_tags import StoryTags


class StoryHeaderMapper:
    """Mapper for StoryHeader conversions."""

    @staticmethod
    def from_spec(spec: Any) -> StoryHeader:
        """Create StoryHeader from specification object.

        Args:
            spec: Specification object (from planning store)

        Returns:
            StoryHeader domain value object

        Raises:
            ValueError: If spec data is invalid
        """
        return StoryHeader(
            story_id=StoryId(value=spec.story_id),
            title=spec.title,
            constraints=StoryConstraints.from_dict(spec.constraints),
            acceptance_criteria=AcceptanceCriteria.from_list(spec.acceptance_criteria),
            tags=StoryTags.from_list(spec.tags),
        )

    @staticmethod
    def to_dict(header: StoryHeader) -> dict[str, Any]:
        """Convert StoryHeader to dictionary for RoleContextFields.

        Used by SessionRehydrationUseCase to populate context packs.

        Args:
            header: StoryHeader value object

        Returns:
            Dictionary representation with primitive types
        """
        return {
            "story_id": header.story_id.to_string(),
            "title": header.title,
            "constraints": header.constraints.to_dict(),
            "acceptance_criteria": header.acceptance_criteria.to_list(),
            "tags": header.tags.to_list(),
        }

