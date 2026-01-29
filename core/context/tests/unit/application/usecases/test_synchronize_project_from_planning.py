"""Unit tests for SynchronizeProjectFromPlanningUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.synchronize_project_from_planning import (
    SynchronizeProjectFromPlanningUseCase,
)
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_save_project() -> None:
    """Execute calls graph.save_project with project entity."""
    graph_command = Mock()
    use_case = SynchronizeProjectFromPlanningUseCase(graph_command=graph_command)
    project = Project(
        project_id=ProjectId("PROJ-1"),
        name="My Project",
        description="",
        status=ProjectStatus("active"),
        owner="",
        created_at_ms=0,
    )

    await use_case.execute(project)

    graph_command.save_project.assert_called_once_with(project)
