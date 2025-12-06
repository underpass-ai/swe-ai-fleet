"""TaskIdParserMapper - Parse task_id format from Orchestrator events.

Mapper (Infrastructure Layer):
- Parses task_id string format used in Orchestrator callbacks
- Extracts ceremony_id, story_id, and role from encoded string
- NO business logic (pure data transformation)

Following Hexagonal Architecture:
- Lives in infrastructure layer
- Converts external format → domain value objects
- Used by NATS consumers
"""

import logging

from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)

logger = logging.getLogger(__name__)


class TaskIdParserMapper:
    """
    Mapper for parsing task_id format from Orchestrator.

    Format: "ceremony-{id}:story-{id}:role-{role}"
    Example: "ceremony-abc123:story-ST-456:role-ARCHITECT"

    Responsibilities:
    - Parse task_id string
    - Extract ceremony_id, story_id, role
    - Validate format and create domain value objects
    """

    @staticmethod
    def parse_task_id(
        task_id: str,
    ) -> tuple[BacklogReviewCeremonyId | None, StoryId | None, BacklogReviewRole | None]:
        """
        Parse task_id to extract ceremony_id, story_id, and role.

        Expected format: "ceremony-{id}:story-{id}:role-{role}"
        Example: "ceremony-abc123:story-ST-456:role-ARCHITECT"

        Args:
            task_id: Encoded task ID string

        Returns:
            Tuple of (ceremony_id, story_id, role) or (None, None, None) if invalid
        """
        try:
            parts = task_id.split(":")
            if len(parts) != 3:
                logger.warning(
                    f"Invalid task_id format: expected 3 parts, got {len(parts)}"
                )
                return (None, None, None)

            ceremony_part = parts[0]  # "ceremony-abc123"
            story_part = parts[1]  # "story-ST-456"
            role_part = parts[2]  # "role-ARCHITECT"

            # Validate prefixes
            if not parts[0].startswith("ceremony-"):
                logger.warning(f"Invalid ceremony prefix in task_id: {parts[0]}")
                return (None, None, None)

            if not parts[1].startswith("story-"):
                logger.warning(f"Invalid story prefix in task_id: {parts[1]}")
                return (None, None, None)

            if not parts[2].startswith("role-"):
                logger.warning(f"Invalid role prefix in task_id: {parts[2]}")
                return (None, None, None)

            # Extract IDs
            ceremony_id_str = ceremony_part.replace("ceremony-", "")
            story_id_str = story_part.replace("story-", "")
            role_str = role_part.replace("role-", "")

            # Create domain value objects (validation happens here)
            ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
            story_id = StoryId(story_id_str)

            # Convert role string to enum
            try:
                role = BacklogReviewRole(role_str)
            except ValueError:
                logger.warning(
                    f"Invalid role in task_id: {role_str}. Must be ARCHITECT, QA, or DEVOPS"
                )
                return (None, None, None)

            return (ceremony_id, story_id, role)

        except ValueError as e:
            logger.warning(f"Failed to parse task_id '{task_id}': {e}")
            return (None, None, None)

        except Exception as e:
            logger.error(f"Unexpected error parsing task_id '{task_id}': {e}")
            return (None, None, None)

