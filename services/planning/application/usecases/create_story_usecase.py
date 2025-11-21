"""Create Story use case."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain import (
    Brief,
    DORScore,
    Story,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId


@dataclass
class CreateStoryUseCase:
    """
    Use Case: Create a new user story.

    Business Rules:
    - Story MUST belong to an Epic (domain invariant)
    - Story starts in DRAFT state
    - Initial DoR score is 0
    - Story ID is auto-generated (UUID)
    - created_by must be provided

    Dependencies:
    - StoragePort: Persist story to Neo4j + Valkey
    - MessagingPort: Publish story.created event
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        epic_id: EpicId,
        title: Title,
        brief: Brief,
        created_by: UserName,
    ) -> Story:
        """
        Create a new story.

        Args:
            epic_id: Parent Epic ID (REQUIRED - domain invariant)
            title: Domain Title value object.
            brief: Domain Brief value object.
            created_by: Domain UserName value object (PO).

        Returns:
            Created story instance.

        Raises:
            ValueError: If epic not found or validation fails
            StorageError: If persistence fails.
            MessagingError: If event publishing fails.
        """
        # Step 1: Validate parent epic exists (domain invariant enforcement)
        parent_epic = await self.storage.get_epic(epic_id)
        if not parent_epic:
            raise ValueError(
                f"Cannot create Story: Epic {epic_id} not found. "
                "Domain Invariant: Story MUST belong to an existing Epic."
            )

        # Validation already done by Value Objects' __post_init__

        # Generate unique story ID
        story_id = StoryId(f"s-{uuid4()}")

        # Create story in DRAFT state with DoR score 0
        now = datetime.now(UTC)
        story = Story(
            story_id=story_id,
            epic_id=epic_id,  # REQUIRED parent reference (domain invariant)
            title=title.value,  # Extract primitive from Value Object
            brief=brief.value,  # Extract primitive from Value Object
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by=created_by.value,  # Extract primitive from Value Object
            created_at=now,
            updated_at=now,
        )

        # Persist to dual storage (Neo4j + Valkey)
        await self.storage.save_story(story)

        # Publish domain event
        await self.messaging.publish_story_created(
            story_id=story_id,  # Pass Value Object directly
            title=title,  # Pass Value Object directly
            created_by=created_by,  # Pass Value Object directly
        )

        return story

