"""Unit tests for ListStoriesUseCase."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from planning.application.usecases import ListStoriesUseCase
from planning.domain import Story, StoryId, StoryState, StoryStateEnum, DORScore


@pytest.mark.asyncio
async def test_list_stories_success():
    """Test successful stories listing."""
    now = datetime.utcnow()
    stories = [
        Story(
            story_id=StoryId("s-001"),
            title="Story 1",
            brief="Brief 1",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
        Story(
            story_id=StoryId("s-002"),
            title="Story 2",
            brief="Brief 2",
            state=StoryState(StoryStateEnum.PO_REVIEW),
            dor_score=DORScore(50),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
    ]
    
    storage = AsyncMock()
    storage.list_stories.return_value = stories
    use_case = ListStoriesUseCase(storage=storage)
    
    result = await use_case.execute()
    
    assert len(result) == 2
    assert result[0].story_id.value == "s-001"
    assert result[1].story_id.value == "s-002"
    
    storage.list_stories.assert_awaited_once_with(
        state_filter=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_stories_with_state_filter():
    """Test listing with state filter."""
    storage = AsyncMock()
    storage.list_stories.return_value = []
    use_case = ListStoriesUseCase(storage=storage)
    
    await use_case.execute(
        state_filter=StoryState(StoryStateEnum.DRAFT),
        limit=50,
        offset=10,
    )
    
    storage.list_stories.assert_awaited_once_with(
        state_filter=StoryState(StoryStateEnum.DRAFT),
        limit=50,
        offset=10,
    )


@pytest.mark.asyncio
async def test_list_stories_rejects_invalid_limit():
    """Test that invalid limit is rejected."""
    storage = AsyncMock()
    use_case = ListStoriesUseCase(storage=storage)
    
    # Limit < 1
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await use_case.execute(limit=0)
    
    # Limit > 1000
    with pytest.raises(ValueError, match="limit must be <= 1000"):
        await use_case.execute(limit=1001)


@pytest.mark.asyncio
async def test_list_stories_rejects_negative_offset():
    """Test that negative offset is rejected."""
    storage = AsyncMock()
    use_case = ListStoriesUseCase(storage=storage)
    
    with pytest.raises(ValueError, match="offset must be >= 0"):
        await use_case.execute(offset=-1)


@pytest.mark.asyncio
async def test_list_stories_defaults():
    """Test default pagination parameters."""
    storage = AsyncMock()
    storage.list_stories.return_value = []
    use_case = ListStoriesUseCase(storage=storage)
    
    await use_case.execute()
    
    # Verify defaults were used
    storage.list_stories.assert_awaited_once_with(
        state_filter=None,
        limit=100,  # Default
        offset=0,   # Default
    )

