"""Unit tests for TransitionStoryUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.transition_story_usecase import (
    InvalidTransitionError,
    StoryNotFoundError,
    TransitionStoryUseCase,
)
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum


@pytest.mark.asyncio
async def test_transition_story_success():
    """Test successful story state transition."""
    # Arrange
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("story-123"),
        title="Title",
        brief="Brief description",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )

    storage_mock = AsyncMock()
    storage_mock.get_story.return_value = story

    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    # Act
    updated_story = await use_case.execute(
        story_id=StoryId("story-123"),
        target_state=StoryState(StoryStateEnum.PO_REVIEW),
        transitioned_by="po-user",
    )

    # Assert
    assert updated_story.state.value == StoryStateEnum.PO_REVIEW

    storage_mock.get_story.assert_awaited_once_with(StoryId("story-123"))
    storage_mock.update_story.assert_awaited_once()
    messaging_mock.publish_story_transitioned.assert_awaited_once_with(
        story_id="story-123",
        from_state="DRAFT",
        to_state="PO_REVIEW",
        transitioned_by="po-user",
    )


@pytest.mark.asyncio
async def test_transition_story_not_found():
    """Test transition story when story doesn't exist."""
    storage_mock = AsyncMock()
    storage_mock.get_story.return_value = None

    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    with pytest.raises(StoryNotFoundError, match="Story not found"):
        await use_case.execute(
            story_id=StoryId("nonexistent"),
            target_state=StoryState(StoryStateEnum.PO_REVIEW),
            transitioned_by="po-user",
        )


@pytest.mark.asyncio
async def test_transition_story_invalid_transition():
    """Test transition story with invalid FSM transition."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("story-123"),
        title="Title",
        brief="Brief description",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )

    storage_mock = AsyncMock()
    storage_mock.get_story.return_value = story

    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    # DRAFT cannot go directly to DONE
    with pytest.raises(InvalidTransitionError, match="Invalid transition"):
        await use_case.execute(
            story_id=StoryId("story-123"),
            target_state=StoryState(StoryStateEnum.DONE),
            transitioned_by="po-user",
        )


@pytest.mark.asyncio
async def test_transition_story_empty_transitioned_by():
    """Test transition story with empty transitioned_by fails."""
    storage_mock = AsyncMock()
    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    with pytest.raises(ValueError, match="transitioned_by cannot be empty"):
        await use_case.execute(
            story_id=StoryId("story-123"),
            target_state=StoryState(StoryStateEnum.PO_REVIEW),
            transitioned_by="",
        )
