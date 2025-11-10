"""Unit tests for CreateTaskUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.entities.story import Story
from planning.domain.entities.task import Task
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.plan_id import PlanId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.task_id import TaskId
from planning.domain.value_objects.task_status import TaskStatus
from planning.domain.value_objects.task_type import TaskType
from planning.domain import DORScore, StoryState, StoryStateEnum


@pytest.mark.asyncio
async def test_create_task_success():
    """Test successful task creation with valid parent story."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story (domain invariant validation)
    story_id = StoryId("US-TEST-001")
    plan_id = PlanId("PLAN-TEST-001")
    mock_story = Story(
        epic_id=EpicId("E-TEST-001"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    # Act
    task = await use_case.execute(
        plan_id=plan_id,
        story_id=story_id,
        title="Implement authentication endpoint",
        description="POST /api/auth/login",
        type=TaskType.DEVELOPMENT,
        assigned_to="dev-agent",
        estimated_hours=4,
        priority=1,
    )

    # Assert
    assert task.plan_id == plan_id
    assert task.story_id == story_id
    assert task.title == "Implement authentication endpoint"
    assert task.description == "POST /api/auth/login"
    assert task.type == TaskType.DEVELOPMENT
    assert task.status == TaskStatus.TODO
    assert task.assigned_to == "dev-agent"
    assert task.estimated_hours == 4
    assert task.priority == 1
    assert isinstance(task.task_id, TaskId)

    # Verify task was saved
    storage.save_task.assert_awaited_once()
    saved_task = storage.save_task.call_args[0][0]
    assert saved_task.title == "Implement authentication endpoint"

    # Verify event was published
    messaging.publish_event.assert_awaited_once()
    call_args = messaging.publish_event.call_args
    assert call_args[1]["topic"] == "planning.task.created"


@pytest.mark.asyncio
async def test_create_task_generates_unique_id():
    """Test that task ID is auto-generated and unique."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-002")
    plan_id = PlanId("PLAN-TEST-002")
    mock_story = Story(
        epic_id=EpicId("E-TEST-002"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    # Create two tasks
    task1 = await use_case.execute(
        plan_id=plan_id,
        story_id=story_id,
        title="Task 1",
    )
    task2 = await use_case.execute(
        plan_id=plan_id,
        story_id=story_id,
        title="Task 2",
    )

    # IDs should be different
    assert task1.task_id != task2.task_id
    assert task1.task_id.value.startswith("T-")
    assert task2.task_id.value.startswith("T-")


@pytest.mark.asyncio
async def test_create_task_rejects_nonexistent_story():
    """Test that creating task without valid parent story fails."""
    storage = AsyncMock()
    storage.get_story.return_value = None  # Story not found
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    story_id = StoryId("NONEXISTENT")
    plan_id = PlanId("PLAN-NONEXISTENT")

    with pytest.raises(ValueError, match="Story .* not found"):
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title="Orphan Task",
        )

    # Task should not be saved
    storage.save_task.assert_not_awaited()
    # Event should not be published
    messaging.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task_rejects_empty_title():
    """Test that empty title is rejected (domain validation)."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-003")
    plan_id = PlanId("PLAN-TEST-003")
    mock_story = Story(
        epic_id=EpicId("E-TEST-003"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    with pytest.raises(ValueError, match="title cannot be empty"):
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title="",
        )


@pytest.mark.asyncio
async def test_create_task_rejects_negative_estimated_hours():
    """Test that negative estimated_hours is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-004")
    plan_id = PlanId("PLAN-TEST-004")
    mock_story = Story(
        epic_id=EpicId("E-TEST-004"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    with pytest.raises(ValueError, match="estimated_hours cannot be negative"):
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title="Test Task",
            estimated_hours=-5,
        )


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_priority():
    """Test that priority < 1 is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-005")
    plan_id = PlanId("PLAN-TEST-005")
    mock_story = Story(
        epic_id=EpicId("E-TEST-005"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    with pytest.raises(ValueError, match="priority must be >= 1"):
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title="Test Task",
            priority=0,
        )


@pytest.mark.asyncio
async def test_create_task_with_all_task_types():
    """Test creating tasks with different types."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-006")
    plan_id = PlanId("PLAN-TEST-006")
    mock_story = Story(
        epic_id=EpicId("E-TEST-006"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    # Test various task types
    for task_type in [TaskType.DEVELOPMENT, TaskType.TESTING, TaskType.REFACTOR]:
        task = await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title=f"Task {task_type.value}",
            type=task_type,
        )
        assert task.type == task_type


@pytest.mark.asyncio
async def test_create_task_storage_failure_propagates():
    """Test that storage failures are propagated."""
    storage = AsyncMock()
    storage.save_task.side_effect = Exception("Storage error")
    messaging = AsyncMock()
    use_case = CreateTaskUseCase(storage=storage, messaging=messaging)

    # Mock parent story
    story_id = StoryId("US-TEST-007")
    plan_id = PlanId("PLAN-TEST-007")
    mock_story = Story(
        epic_id=EpicId("E-TEST-007"),
        story_id=story_id,
        title="Test Story",
        brief="Test Brief",
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by="po",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_story.return_value = mock_story

    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            title="Test Task",
        )

    # Event should not be published on storage failure
    messaging.publish_event.assert_not_awaited()

