"""Unit tests for ListTasksUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType


def _make_task(
    task_id: str,
    story_id: str,
    plan_id: str | None = None,
) -> Task:
    return Task(
        task_id=TaskId(task_id),
        story_id=StoryId(story_id),
        title="Task",
        description="",
        type=TaskType(TaskType.DEVELOPMENT),
        status=TaskStatus(TaskStatus.TODO),
        assigned_to="",
        estimated_hours=0,
        priority=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        plan_id=PlanId(plan_id) if plan_id else None,
    )


@pytest.mark.asyncio
async def test_list_tasks_no_filter():
    """execute returns all tasks from storage when no story_id or plan_id."""
    storage = AsyncMock()
    tasks = [
        _make_task("T1", "story-1"),
        _make_task("T2", "story-1"),
    ]
    storage.list_tasks = AsyncMock(return_value=tasks)
    use_case = ListTasksUseCase(storage=storage)

    result = await use_case.execute(limit=100, offset=0)

    assert result == tasks
    storage.list_tasks.assert_awaited_once_with(
        story_id=None, limit=100, offset=0
    )


@pytest.mark.asyncio
async def test_list_tasks_with_story_id():
    """execute passes story_id to storage."""
    storage = AsyncMock()
    storage.list_tasks = AsyncMock(return_value=[])
    use_case = ListTasksUseCase(storage=storage)
    story_id = StoryId("story-1")

    await use_case.execute(story_id=story_id, limit=10, offset=0)

    storage.list_tasks.assert_awaited_once_with(
        story_id=story_id, limit=10, offset=0
    )


@pytest.mark.asyncio
async def test_list_tasks_with_plan_id_filters_in_memory():
    """execute filters by plan_id in memory when storage returns tasks."""
    storage = AsyncMock()
    plan_id = PlanId("plan-1")
    task_in_plan = _make_task("T1", "story-1", "plan-1")
    task_other = _make_task("T2", "story-1", "plan-2")
    storage.list_tasks = AsyncMock(return_value=[task_in_plan, task_other])
    use_case = ListTasksUseCase(storage=storage)

    result = await use_case.execute(plan_id=plan_id, limit=100, offset=0)

    assert len(result) == 1
    assert result[0].task_id.value == "T1"
    assert result[0].plan_id == plan_id
