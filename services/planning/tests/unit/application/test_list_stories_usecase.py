"""Unit tests for ListStoriesUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases import ListStoriesUseCase
from planning.domain import DORScore, Story, StoryId, StoryList, StoryState, StoryStateEnum
from planning.domain.value_objects.identifiers.epic_id import EpicId


@pytest.mark.asyncio
async def test_list_stories_by_state():
    """Test listing stories by state."""
    # Arrange
    now = datetime.now(UTC)
    epic_id = EpicId("E-TEST-001")
    stories = [
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-1"),
            title="Story 1",
            brief="Brief 1",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-2"),
            title="Story 2",
            brief="Brief 2",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
    ]

    storage_mock = AsyncMock()
    storage_mock.list_stories.return_value = StoryList(stories)

    use_case = ListStoriesUseCase(storage=storage_mock)

    # Act
    result = await use_case.execute(state_filter=StoryState(StoryStateEnum.DRAFT))

    # Assert
    assert len(result) == 2
    assert result[0].story_id.value == "story-1"
    assert result[1].story_id.value == "story-2"

    storage_mock.list_stories.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_all_stories():
    """Test listing all stories (no state filter)."""
    now = datetime.now(UTC)
    epic_id = EpicId("E-TEST-002")
    stories = [
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-1"),
            title="Story 1",
            brief="Brief 1",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-2"),
            title="Story 2",
            brief="Brief 2",
            state=StoryState(StoryStateEnum.PO_REVIEW),
            dor_score=DORScore(50),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
    ]

    storage_mock = AsyncMock()
    storage_mock.list_stories.return_value = StoryList(stories)

    use_case = ListStoriesUseCase(storage=storage_mock)

    # Act
    result = await use_case.execute(state_filter=None)

    # Assert
    assert len(result) == 2

    storage_mock.list_stories.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_stories_empty():
    """Test listing stories when none exist."""
    storage_mock = AsyncMock()
    storage_mock.list_stories.return_value = StoryList([])

    use_case = ListStoriesUseCase(storage=storage_mock)

    # Act
    result = await use_case.execute(state_filter=StoryState(StoryStateEnum.DRAFT))

    # Assert
    assert len(result) == 0


@pytest.mark.asyncio
async def test_list_stories_validates_limit_too_small():
    """Test that limit < 1 raises ValueError."""
    storage_mock = AsyncMock()
    use_case = ListStoriesUseCase(storage=storage_mock)

    with pytest.raises(ValueError, match="limit must be >= 1"):
        await use_case.execute(limit=0)


@pytest.mark.asyncio
async def test_list_stories_validates_limit_too_large():
    """Test that limit > 1000 raises ValueError."""
    storage_mock = AsyncMock()
    use_case = ListStoriesUseCase(storage=storage_mock)

    with pytest.raises(ValueError, match="limit must be <= 1000"):
        await use_case.execute(limit=1001)


@pytest.mark.asyncio
async def test_list_stories_validates_offset_negative():
    """Test that offset < 0 raises ValueError."""
    storage_mock = AsyncMock()
    use_case = ListStoriesUseCase(storage=storage_mock)

    with pytest.raises(ValueError, match="offset must be >= 0"):
        await use_case.execute(offset=-1)


@pytest.mark.asyncio
async def test_list_stories_with_pagination():
    """Test listing stories with pagination (limit and offset)."""
    now = datetime.now(UTC)
    epic_id = EpicId("E-TEST-003")
    stories = [
        Story(
            epic_id=epic_id,
            story_id=StoryId(f"story-{i}"),
            title=f"Story {i}",
            brief=f"Brief {i}",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        )
        for i in range(1, 6)  # 5 stories
    ]

    storage_mock = AsyncMock()
    storage_mock.list_stories.return_value = StoryList(stories[2:4])  # Return stories 3-4 (offset=2, limit=2)

    use_case = ListStoriesUseCase(storage=storage_mock)

    # Act: Request page 2 (offset=2, limit=2)
    result = await use_case.execute(limit=2, offset=2)

    # Assert
    assert len(result) == 2
    storage_mock.list_stories.assert_awaited_once_with(
        state_filter=None,
        limit=2,
        offset=2,
    )
