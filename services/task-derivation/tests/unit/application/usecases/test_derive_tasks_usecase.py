"""Tests for DeriveTasksUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.domain.value_objects.content.acceptance_criteria import (
    AcceptanceCriteria,
)
from task_derivation.domain.value_objects.content.plan_description import PlanDescription
from task_derivation.domain.value_objects.content.technical_notes import TechnicalNotes
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from core.shared.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.domain.value_objects.task_derivation.requests.task_derivation_request import (
    TaskDerivationRequest,
)


@pytest.mark.asyncio
async def test_execute_submits_prompt_to_ray() -> None:
    planning_port = AsyncMock()
    context_port = AsyncMock()
    ray_executor = AsyncMock()

    plan_context = PlanContext(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        title=Title("New Feature"),
        description=PlanDescription("Implement feature"),
        acceptance_criteria=AcceptanceCriteria.from_iterable(("AC1",)),
        technical_notes=TechnicalNotes("Notes"),
        roles=(ContextRole("DEVELOPER"),),
    )
    planning_port.get_plan.return_value = plan_context
    context_port.get_context.return_value = "context blocks"
    ray_executor.submit_task_derivation.return_value = AsyncMock()

    config = TaskDerivationConfig(
        prompt_template="{description}\n{acceptance_criteria}",
        min_tasks=1,
        max_tasks=5,
        max_retries=2,
    )

    usecase = DeriveTasksUseCase(
        planning_port=planning_port,
        context_port=context_port,
        ray_executor_port=ray_executor,
        config=config,
    )

    request = TaskDerivationRequest(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        roles=(ContextRole("DEVELOPER"),),
        requested_by="user-1",
    )

    await usecase.execute(request)

    planning_port.get_plan.assert_awaited_once_with(PlanId("plan-1"))
    context_port.get_context.assert_awaited_once()
    ray_executor.submit_task_derivation.assert_awaited()

