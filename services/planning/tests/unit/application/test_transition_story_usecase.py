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
from planning.domain.value_objects.identifiers.epic_id import EpicId


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


@pytest.mark.asyncio
async def test_transition_to_ready_for_execution_without_tasks():
    """Test that transition to READY_FOR_EXECUTION fails when story has no tasks."""
    from planning.application.usecases.transition_story_usecase import TasksNotReadyError

    now = datetime.now(UTC)
    story = Story(
        epic_id=EpicId("E-TEST-TRANS-003"),
        story_id=StoryId("story-123"),
        title="Title",
        brief="Brief description",
        state=StoryState(StoryStateEnum.PLANNED),  # PLANNED can transition to READY_FOR_EXECUTION
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )

    storage_mock = AsyncMock()
    storage_mock.get_story.return_value = story
    storage_mock.list_tasks.return_value = []  # No tasks

    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    # Act & Assert
    with pytest.raises(TasksNotReadyError, match="No tasks defined"):
        await use_case.execute(
            story_id=StoryId("story-123"),
            target_state=StoryState(StoryStateEnum.READY_FOR_EXECUTION),
            transitioned_by=UserName("po-user"),
        )

    # Assert: Notification sent to PO
    messaging_mock.publish_story_tasks_not_ready.assert_awaited_once()
    call_args = messaging_mock.publish_story_tasks_not_ready.call_args[1]
    assert call_args["story_id"].value == "story-123"
    assert "No tasks defined" in call_args["reason"]
    assert call_args["total_tasks"] == 0


@pytest.mark.asyncio
async def test_transition_to_ready_for_execution_with_tasks_without_priority():
    """Test that transition to READY_FOR_EXECUTION fails when tasks have invalid priority."""
    from planning.application.usecases.transition_story_usecase import TasksNotReadyError
    from planning.domain.value_objects.identifiers.task_id import TaskId

    now = datetime.now(UTC)
    story = Story(
        epic_id=EpicId("E-TEST-TRANS-004"),
        story_id=StoryId("story-123"),
        title="Title",
        brief="Brief description",
        state=StoryState(StoryStateEnum.PLANNED),  # PLANNED can transition to READY_FOR_EXECUTION
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )

    # Create a mock task with invalid priority (priority < 1 means not set)
    # Note: We can't use Task entity directly because it validates priority >= 1
    # This simulates data from storage that might have invalid priorities (legacy data)
    from types import SimpleNamespace

    task_without_priority = SimpleNamespace(
        task_id=TaskId("task-001"),
        priority=0,  # Invalid - not set by LLM
    )

    storage_mock = AsyncMock()
    storage_mock.get_story.return_value = story
    storage_mock.list_tasks.return_value = [task_without_priority]

    messaging_mock = AsyncMock()

    use_case = TransitionStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    # Act & Assert
    with pytest.raises(TasksNotReadyError, match="tasks without priority"):
        await use_case.execute(
            story_id=StoryId("story-123"),
            target_state=StoryState(StoryStateEnum.READY_FOR_EXECUTION),
            transitioned_by=UserName("po-user"),
        )

    # Assert: Notification sent to PO
    messaging_mock.publish_story_tasks_not_ready.assert_awaited_once()
    call_args = messaging_mock.publish_story_tasks_not_ready.call_args[1]
    assert call_args["story_id"].value == "story-123"
    assert "tasks without priority" in call_args["reason"]
    assert len(call_args["task_ids_without_priority"]) == 1
    assert call_args["total_tasks"] == 1
