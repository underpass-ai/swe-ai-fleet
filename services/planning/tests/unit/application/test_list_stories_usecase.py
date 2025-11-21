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
