"""Unit tests for GetStoryUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.get_story_usecase import GetStoryUseCase
from planning.domain.entities.story import Story
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.statuses.story_state import StoryState, StoryStateEnum
from planning.domain.value_objects.scoring.dor_score import DORScore
from planning.domain.value_objects.actors.user_name import UserName


@pytest.mark.asyncio
async def test_get_story_found():
    """execute returns story when storage returns it."""
    storage = AsyncMock()
    story_id = StoryId("story-1")
    mock_story = Story(
        epic_id=EpicId("E-1"),
        story_id=story_id,
        title=Title("Story 1"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story = AsyncMock(return_value=mock_story)
    use_case = GetStoryUseCase(storage=storage)

    result = await use_case.execute(story_id=story_id)

    assert result is mock_story
    storage.get_story.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_get_story_not_found():
    """execute returns None when storage returns None."""
    storage = AsyncMock()
    storage.get_story = AsyncMock(return_value=None)
    use_case = GetStoryUseCase(storage=storage)
    story_id = StoryId("story-missing")

    result = await use_case.execute(story_id=story_id)

    assert result is None
    storage.get_story.assert_awaited_once_with(story_id)
