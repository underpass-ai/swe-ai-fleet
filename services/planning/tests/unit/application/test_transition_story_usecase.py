"""Unit tests for TransitionStoryUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.transition_story_usecase import (
    InvalidTransitionError,
    StoryNotFoundError,
    TransitionStoryUseCase,
)
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum, UserName
from planning.domain.value_objects.epic_id import EpicId


@pytest.mark.asyncio
async def test_transition_story_success():
    """Test successful story state transition."""
    # Arrange
    now = datetime.now(UTC)
    story = Story(
        epic_id=EpicId("E-TEST-TRANS-001"),
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
        transitioned_by=UserName("po-user"),
    )

    # Assert
    assert updated_story.state.value == StoryStateEnum.PO_REVIEW

    storage_mock.get_story.assert_awaited_once_with(StoryId("story-123"))
    storage_mock.update_story.assert_awaited_once()

    # Verify event published with Value Objects
    call_args = messaging_mock.publish_story_transitioned.call_args[1]
    assert call_args["story_id"].value == "story-123"
    assert call_args["from_state"].value == StoryStateEnum.DRAFT
    assert call_args["to_state"].value == StoryStateEnum.PO_REVIEW
    assert call_args["transitioned_by"].value == "po-user"


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
            transitioned_by=UserName("po-user"),
        )


@pytest.mark.asyncio
async def test_transition_story_invalid_transition():
    """Test transition story with invalid FSM transition."""
    now = datetime.now(UTC)
    story = Story(
        epic_id=EpicId("E-TEST-TRANS-002"),
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
            transitioned_by=UserName("po-user"),
        )


@pytest.mark.asyncio
async def test_transition_story_rejects_empty_transitioned_by():
    """Test that empty transitioned_by is rejected (by UserName validation)."""
    # UserName validation fails before use case executes
    with pytest.raises(ValueError, match="UserName cannot be empty"):
        UserName("")
