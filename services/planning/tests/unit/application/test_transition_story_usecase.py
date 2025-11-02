"""Unit tests for TransitionStoryUseCase."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from planning.application.usecases import (
    TransitionStoryUseCase,
    StoryNotFoundError,
    InvalidTransitionError,
)
from planning.domain import Story, StoryId, StoryState, StoryStateEnum, DORScore


@pytest.mark.asyncio
async def test_transition_story_success():
    """Test successful story transition."""
    # Arrange
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    storage = AsyncMock()
    storage.get_story.return_value = story
    messaging = AsyncMock()
    use_case = TransitionStoryUseCase(storage=storage, messaging=messaging)
    
    # Act
    updated = await use_case.execute(
        story_id=StoryId("s-001"),
        target_state=StoryState(StoryStateEnum.PO_REVIEW),
        transitioned_by="po-001",
    )
    
    # Assert
    assert updated.state.value == StoryStateEnum.PO_REVIEW
    
    # Verify storage was called
    storage.get_story.assert_awaited_once_with(StoryId("s-001"))
    storage.update_story.assert_awaited_once()
    
    # Verify event was published
    messaging.publish_story_transitioned.assert_awaited_once()
    args = messaging.publish_story_transitioned.call_args[1]
    assert args["story_id"] == "s-001"
    assert args["from_state"] == "DRAFT"
    assert args["to_state"] == "PO_REVIEW"
    assert args["transitioned_by"] == "po-001"


@pytest.mark.asyncio
async def test_transition_story_not_found():
    """Test transition when story doesn't exist."""
    storage = AsyncMock()
    storage.get_story.return_value = None  # Story not found
    messaging = AsyncMock()
    use_case = TransitionStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(StoryNotFoundError, match="Story not found"):
        await use_case.execute(
            story_id=StoryId("s-999"),
            target_state=StoryState(StoryStateEnum.PO_REVIEW),
            transitioned_by="po",
        )
    
    # Verify update was NOT called
    storage.update_story.assert_not_awaited()
    messaging.publish_story_transitioned.assert_not_awaited()


@pytest.mark.asyncio
async def test_transition_story_invalid_transition():
    """Test invalid FSM transition."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    storage = AsyncMock()
    storage.get_story.return_value = story
    messaging = AsyncMock()
    use_case = TransitionStoryUseCase(storage=storage, messaging=messaging)
    
    # DRAFT → DONE is invalid (must go through intermediate states)
    with pytest.raises(InvalidTransitionError, match="Invalid transition"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            target_state=StoryState(StoryStateEnum.DONE),
            transitioned_by="po",
        )
    
    # Verify update was NOT called
    storage.update_story.assert_not_awaited()
    messaging.publish_story_transitioned.assert_not_awaited()


@pytest.mark.asyncio
async def test_transition_story_rejects_empty_transitioned_by():
    """Test that empty transitioned_by is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = TransitionStoryUseCase(storage=storage, messaging=messaging)
    
    with pytest.raises(ValueError, match="transitioned_by cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            target_state=StoryState(StoryStateEnum.PO_REVIEW),
            transitioned_by="",
        )

