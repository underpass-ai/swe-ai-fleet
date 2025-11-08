"""StoryAuthorizationPort - Port for checking story access authorization."""

from typing import Protocol

from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.epic_id import EpicId


class StoryAuthorizationPort(Protocol):
    """Port for checking if user is authorized to access a story.

    Used for RBAC L2 (row-level security) to verify:
    - Is story assigned to user?
    - Does story belong to user's assigned epic?
    - Is story in testing phase (for QA)?
    - etc.
    """

    async def is_story_assigned_to_user(
        self,
        story_id: StoryId,
        user_id: str,
    ) -> bool:
        """Check if story is assigned to user.

        Args:
            story_id: Story to check
            user_id: User identifier

        Returns:
            True if story is assigned to user
        """
        ...

    async def get_epic_for_story(
        self,
        story_id: StoryId,
    ) -> EpicId:
        """Get epic that contains this story.

        Args:
            story_id: Story identifier

        Returns:
            Epic identifier

        Raises:
            ValueError: If story not found or has no epic
        """
        ...

    async def is_epic_assigned_to_user(
        self,
        epic_id: EpicId,
        user_id: str,
    ) -> bool:
        """Check if epic is assigned to user.

        Args:
            epic_id: Epic to check
            user_id: User identifier (e.g., architect_id)

        Returns:
            True if epic is assigned to user
        """
        ...

    async def is_story_in_testing_phase(
        self,
        story_id: StoryId,
    ) -> bool:
        """Check if story is in testing phase.

        Args:
            story_id: Story identifier

        Returns:
            True if story status is TESTING or QA_REVIEW
        """
        ...

