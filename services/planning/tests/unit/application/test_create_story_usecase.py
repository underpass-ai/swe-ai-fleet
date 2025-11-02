"""Unit tests for CreateStoryUseCase."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from planning.application.usecases import CreateStoryUseCase
from planning.domain import Story, StoryState, StoryStateEnum, DORScore


@pytest.mark.asyncio
async def test_create_story_success():
    """Test successful story creation."""
    # Arrange
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    # Act
    story = await use_case.execute(
        title="As a user, I want authentication",
        brief="Implement JWT auth",
        created_by="po-001",
    )
    
    # Assert
    assert story.title == "As a user, I want authentication"
    assert story.brief == "Implement JWT auth"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 0
    assert story.created_by == "po-001"
    assert story.story_id.value.startswith("s-")
    
    # Verify storage was called
    storage.save_story.assert_awaited_once()
    saved_story = storage.save_story.call_args[0][0]
    assert saved_story.title == "As a user, I want authentication"
    
    # Verify event was published
    messaging.publish_story_created.assert_awaited_once_with(
        story_id=story.story_id.value,
        title="As a user, I want authentication",
        created_by="po-001",
    )


@pytest.mark.asyncio
async def test_create_story_strips_whitespace():
    """Test that whitespace is stripped from inputs."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    story = await use_case.execute(
        title="  Title with spaces  ",
        brief="  Brief with spaces  ",
        created_by="  po-001  ",
    )
    
    assert story.title == "Title with spaces"
    assert story.brief == "Brief with spaces"
    assert story.created_by == "po-001"


@pytest.mark.asyncio
async def test_create_story_rejects_empty_title():
    """Test that empty title is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(ValueError, match="title cannot be empty"):
        await use_case.execute(
            title="",
            brief="Brief",
            created_by="po",
        )
    
    # Verify storage was NOT called
    storage.save_story.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_story_rejects_empty_brief():
    """Test that empty brief is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(ValueError, match="brief cannot be empty"):
        await use_case.execute(
            title="Title",
            brief="",
            created_by="po",
        )


@pytest.mark.asyncio
async def test_create_story_rejects_empty_created_by():
    """Test that empty created_by is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(ValueError, match="created_by cannot be empty"):
        await use_case.execute(
            title="Title",
            brief="Brief",
            created_by="",
        )


@pytest.mark.asyncio
async def test_create_story_storage_failure_propagates():
    """Test that storage errors are propagated."""
    storage = AsyncMock()
    storage.save_story.side_effect = Exception("Neo4j connection failed")
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(Exception, match="Neo4j connection failed"):
        await use_case.execute(
            title="Title",
            brief="Brief",
            created_by="po",
        )


@pytest.mark.asyncio
async def test_create_story_messaging_failure_propagates():
    """Test that messaging errors are propagated."""
    storage = AsyncMock()
    messaging = AsyncMock()
    messaging.publish_story_created.side_effect = Exception("NATS unavailable")
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(Exception, match="NATS unavailable"):
        await use_case.execute(
            title="Title",
            brief="Brief",
            created_by="po",
        )

