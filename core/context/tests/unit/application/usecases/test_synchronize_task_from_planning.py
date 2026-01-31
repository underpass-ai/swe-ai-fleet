"""Unit tests for SynchronizeTaskFromPlanningUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.synchronize_task_from_planning import (
    SynchronizeTaskFromPlanningUseCase,
)
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.task import Task
from core.context.domain.task_status import TaskStatus
from core.context.domain.task_type import TaskType

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_save_task() -> None:
    """Execute calls graph.save_task with task entity."""
    graph_command = Mock()
    use_case = SynchronizeTaskFromPlanningUseCase(graph_command=graph_command)
    task = Task(
        task_id=TaskId("T-1"),
        plan_id=PlanId("P-1"),
        title="Implement login",
        type=TaskType("development"),
        status=TaskStatus("todo"),
    )

    await use_case.execute(task)

    graph_command.save_task.assert_called_once_with(task)
