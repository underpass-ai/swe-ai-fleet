"""Tests for ProcessTaskDerivationResultUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority

from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


@pytest.mark.asyncio
async def test_process_success_publishes_completed_event() -> None:
    planning_port = AsyncMock()
    messaging_port = AsyncMock()
    clock = lambda: datetime(2025, 1, 1, tzinfo=UTC)

    usecase = ProcessTaskDerivationResultUseCase(
        planning_port=planning_port,
        messaging_port=messaging_port,
        clock=clock,
    )

    task_node = TaskNode(
        task_id=AsyncMock(),
        title=Title("Task A"),
        description=TaskDescription("Do something"),
        keywords=(),
        estimated_hours=Duration(4),
        priority=Priority(1),
    )

    await usecase.execute(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        role=ContextRole("DEVELOPER"),
        task_nodes=(task_node,),
    )

    planning_port.create_tasks.assert_awaited()
    messaging_port.publish_task_derivation_completed.assert_awaited()


@pytest.mark.asyncio
async def test_process_failure_publishes_failed_event() -> None:
    planning_port = AsyncMock()
    messaging_port = AsyncMock()
    planning_port.create_tasks.side_effect = RuntimeError("DB down")

    usecase = ProcessTaskDerivationResultUseCase(
        planning_port=planning_port,
        messaging_port=messaging_port,
    )

    task_node = TaskNode(
        task_id=AsyncMock(),
        title=Title("Task A"),
        description=TaskDescription("Do something"),
        keywords=(),
        estimated_hours=Duration(4),
        priority=Priority(1),
    )

    with pytest.raises(RuntimeError):
        await usecase.execute(
            plan_id=PlanId("plan-1"),
            story_id=StoryId("story-1"),
            role=ContextRole("DEVELOPER"),
            task_nodes=(task_node,),
        )

    messaging_port.publish_task_derivation_failed.assert_awaited()

