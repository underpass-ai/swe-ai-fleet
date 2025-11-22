"""Unit tests for CreateTaskUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain import DORScore, StoryState, StoryStateEnum
from planning.domain.entities.story import Story
from planning.domain.value_objects.actors.role import Role, RoleType
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.requests.create_task_request import CreateTaskRequest
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType


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

    # Build CreateTaskRequest VO
    request = CreateTaskRequest(
        plan_id=plan_id,
        story_id=story_id,
        task_id=TaskId(f"T-{uuid4()}"),
        title=Title("Implement authentication endpoint"),
        description=TaskDescription("POST /api/auth/login"),
        task_type=TaskType.DEVELOPMENT,
        assigned_to=Role(RoleType.DEVELOPER),
        estimated_hours=Duration(4),
        priority=Priority(1),
    )

    # Act
    task = await use_case.execute(request)

    # Assert
    assert task.plan_id == plan_id
    assert task.story_id == story_id
    assert task.title == "Implement authentication endpoint"
    assert task.description == "POST /api/auth/login"
    assert task.type == TaskType.DEVELOPMENT
    assert task.status == TaskStatus.TODO
    assert task.assigned_to == "DEV"  # Role VO converts to enum value string
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

    # Create two tasks with different IDs
    request1 = CreateTaskRequest(
        plan_id=plan_id,
        story_id=story_id,
        task_id=TaskId(f"T-{uuid4()}"),
        title=Title("Task 1"),
        description=TaskDescription("Task 1 description"),
        task_type=TaskType.DEVELOPMENT,
        assigned_to=Role(RoleType.DEVELOPER),
        estimated_hours=Duration(0),
        priority=Priority(1),
    )
    request2 = CreateTaskRequest(
        plan_id=plan_id,
        story_id=story_id,
        task_id=TaskId(f"T-{uuid4()}"),
        title=Title("Task 2"),
        description=TaskDescription("Task 2 description"),
        task_type=TaskType.DEVELOPMENT,
        assigned_to=Role(RoleType.DEVELOPER),
        estimated_hours=Duration(0),
        priority=Priority(1),
    )

    task1 = await use_case.execute(request1)
    task2 = await use_case.execute(request2)

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

    request = CreateTaskRequest(
        plan_id=plan_id,
        story_id=story_id,
        task_id=TaskId(f"T-{uuid4()}"),
        title=Title("Orphan Task"),
        description=TaskDescription("Orphan task description"),
        task_type=TaskType.DEVELOPMENT,
        assigned_to=Role(RoleType.DEVELOPER),
        estimated_hours=Duration(0),
        priority=Priority(1),
    )

    with pytest.raises(ValueError, match="Story .* not found"):
        await use_case.execute(request)

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

    # Title validation happens in Title VO, not in use case
    with pytest.raises(ValueError, match="Title cannot be empty"):
        request = CreateTaskRequest(
            plan_id=plan_id,
            story_id=story_id,
            task_id=TaskId(f"T-{uuid4()}"),
            title=Title(""),  # This will raise ValueError
            description=TaskDescription("Description"),
            task_type=TaskType.DEVELOPMENT,
            assigned_to=Role(RoleType.DEVELOPER),
            estimated_hours=Duration(0),
            priority=Priority(1),
        )
        await use_case.execute(request)


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

    # Validation happens in Duration VO
    with pytest.raises(ValueError, match="Duration hours cannot be negative"):
        request = CreateTaskRequest(
            plan_id=plan_id,
            story_id=story_id,
            task_id=TaskId(f"T-{uuid4()}"),
            title=Title("Test Task"),
            description=TaskDescription("Test description"),
            task_type=TaskType.DEVELOPMENT,
            assigned_to=Role(RoleType.DEVELOPER),
            estimated_hours=Duration(-5),  # This will raise ValueError (Duration validates >= 0)
            priority=Priority(1),
        )
        await use_case.execute(request)


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

    # Validation happens in Priority VO
    with pytest.raises(ValueError, match="Priority must be >= 1"):
        request = CreateTaskRequest(
            plan_id=plan_id,
            story_id=story_id,
            task_id=TaskId(f"T-{uuid4()}"),
            title=Title("Test Task"),
            description=TaskDescription("Test description"),
            task_type=TaskType.DEVELOPMENT,
            assigned_to=Role(RoleType.DEVELOPER),
            estimated_hours=Duration(0),
            priority=Priority(0),  # This will raise ValueError (Priority validates >= 1)
        )
        await use_case.execute(request)


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
        request = CreateTaskRequest(
            plan_id=plan_id,
            story_id=story_id,
            task_id=TaskId(f"T-{uuid4()}"),
            title=Title(f"Task {task_type.value}"),
            description=TaskDescription(f"Task {task_type.value} description"),
            task_type=task_type,
            assigned_to=Role(RoleType.DEVELOPER),
            estimated_hours=Duration(0),
            priority=Priority(1),
        )
        task = await use_case.execute(request)
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

    request = CreateTaskRequest(
        plan_id=plan_id,
        story_id=story_id,
        task_id=TaskId(f"T-{uuid4()}"),
        title=Title("Test Task"),
        description=TaskDescription("Test description"),
        task_type=TaskType.DEVELOPMENT,
        assigned_to=Role(RoleType.DEVELOPER),
        estimated_hours=Duration(0),
        priority=Priority(1),
    )

    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(request)

    # Event should not be published on storage failure
    messaging.publish_event.assert_not_awaited()

