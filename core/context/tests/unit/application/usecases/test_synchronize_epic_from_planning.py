"""Unit tests for SynchronizeEpicFromPlanningUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.synchronize_epic_from_planning import (
    SynchronizeEpicFromPlanningUseCase,
)
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_save_epic() -> None:
    """Execute calls graph.save_epic with epic entity."""
    graph_command = Mock()
    use_case = SynchronizeEpicFromPlanningUseCase(graph_command=graph_command)
    epic = Epic(
        epic_id=EpicId("E-1"),
        project_id=ProjectId("PROJ-1"),
        title="Authentication",
        description="",
        status=EpicStatus.ACTIVE,
        created_at_ms=0,
    )

    await use_case.execute(epic)

    graph_command.save_epic.assert_called_once_with(epic)
