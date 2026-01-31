"""Unit tests for GetEpicUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.get_epic_usecase import GetEpicUseCase
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus


@pytest.mark.asyncio
async def test_get_epic_found():
    """execute returns epic when storage returns it."""
    storage = AsyncMock()
    epic_id = EpicId("E-1")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-1"),
        title="Epic 1",
        description="Desc",
        status=EpicStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic = AsyncMock(return_value=mock_epic)
    use_case = GetEpicUseCase(storage=storage)

    result = await use_case.execute(epic_id=epic_id)

    assert result is mock_epic
    storage.get_epic.assert_awaited_once_with(epic_id)


@pytest.mark.asyncio
async def test_get_epic_not_found():
    """execute returns None and logs warning when storage returns None."""
    storage = AsyncMock()
    storage.get_epic = AsyncMock(return_value=None)
    use_case = GetEpicUseCase(storage=storage)
    epic_id = EpicId("E-MISSING")

    result = await use_case.execute(epic_id=epic_id)

    assert result is None
    storage.get_epic.assert_awaited_once_with(epic_id)
