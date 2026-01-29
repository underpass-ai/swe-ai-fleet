"""Unit tests for RecordPlanApprovalUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.record_plan_approval import (
    RecordPlanApprovalUseCase,
)
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.plan_approval import PlanApproval

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_save_plan_approval() -> None:
    """Execute calls graph.save_plan_approval with approval entity."""
    graph_command = Mock()
    use_case = RecordPlanApprovalUseCase(graph_command=graph_command)
    approval = PlanApproval(
        plan_id=PlanId("P-1"),
        story_id=StoryId("s-1"),
        approved_by="po@test",
        timestamp="2025-01-01T12:00:00Z",
    )

    await use_case.execute(approval)

    graph_command.save_plan_approval.assert_called_once_with(approval)
