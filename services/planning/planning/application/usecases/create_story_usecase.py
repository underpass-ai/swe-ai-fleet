"""Create Story use case."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from planning.application.ports import StoragePort, MessagingPort
from planning.domain import Story, StoryId, StoryState, StoryStateEnum, DORScore


@dataclass
class CreateStoryUseCase:
    """
    Use Case: Create a new user story.
    
    Business Rules:
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
        title: str,
        brief: str,
        created_by: str,
    ) -> Story:
        """
        Create a new story.
        
        Args:
            title: Story title (user story format recommended).
            brief: Brief description with acceptance criteria.
            created_by: User/PO who created the story.
        
        Returns:
            Created story instance.
        
        Raises:
            ValueError: If title or brief is empty.
            StorageError: If persistence fails.
            MessagingError: If event publishing fails.
        """
        # Validate inputs (fail-fast)
        if not title or not title.strip():
            raise ValueError("Story title cannot be empty")
        
        if not brief or not brief.strip():
            raise ValueError("Story brief cannot be empty")
        
        if not created_by or not created_by.strip():
            raise ValueError("created_by cannot be empty")
        
        # Generate unique story ID
        story_id = StoryId(f"s-{uuid4()}")
        
        # Create story in DRAFT state with DoR score 0
        now = datetime.now(timezone.utc)
        story = Story(
            story_id=story_id,
            title=title.strip(),
            brief=brief.strip(),
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by=created_by.strip(),
            created_at=now,
            updated_at=now,
        )
        
        # Persist to dual storage (Neo4j + Valkey)
        await self.storage.save_story(story)
        
        # Publish domain event
        await self.messaging.publish_story_created(
            story_id=story_id.value,
            title=title,
            created_by=created_by,
        )
        
        return story

