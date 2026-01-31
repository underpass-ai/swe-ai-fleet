"""Unit tests for GetTaskUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.get_task_usecase import GetTaskUseCase
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType


@pytest.mark.asyncio
async def test_get_task_found():
    """execute returns task when storage returns it."""
    storage = AsyncMock()
    task_id = TaskId("TASK-1")
    mock_task = Task(
        task_id=task_id,
        story_id=StoryId("story-1"),
        title="Task 1",
        description="Desc",
        type=TaskType(TaskType.DEVELOPMENT),
        status=TaskStatus(TaskStatus.TODO),
        assigned_to="dev",
        estimated_hours=8,
        priority=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_task = AsyncMock(return_value=mock_task)
    use_case = GetTaskUseCase(storage=storage)

    result = await use_case.execute(task_id=task_id)

    assert result is mock_task
    storage.get_task.assert_awaited_once_with(task_id)


@pytest.mark.asyncio
async def test_get_task_not_found():
    """execute returns None when storage returns None."""
    storage = AsyncMock()
    storage.get_task = AsyncMock(return_value=None)
    use_case = GetTaskUseCase(storage=storage)
    task_id = TaskId("TASK-MISSING")

    result = await use_case.execute(task_id=task_id)

    assert result is None
    storage.get_task.assert_awaited_once_with(task_id)
