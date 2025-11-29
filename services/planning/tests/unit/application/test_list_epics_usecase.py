"""Tests for ListEpicsUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.list_epics_usecase import ListEpicsUseCase
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus


def _build_epic() -> Epic:
    now = datetime.now(UTC)
    return Epic(
        epic_id=EpicId("E-1"),
        project_id=ProjectId("PROJ-1"),
        title="Sample",
        description="desc",
        status=EpicStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_epics_returns_storage_results() -> None:
    storage = AsyncMock()
    epic = _build_epic()
    storage.list_epics.return_value = [epic]

    use_case = ListEpicsUseCase(storage=storage)
    result = await use_case.execute(project_id=epic.project_id)

    assert result == [epic]
    storage.list_epics.assert_awaited_once_with(
        project_id=epic.project_id,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_epics_handles_none_response() -> None:
    storage = AsyncMock()
    storage.list_epics.return_value = None

    use_case = ListEpicsUseCase(storage=storage)
    result = await use_case.execute()

    assert result == []


@pytest.mark.asyncio
async def test_list_epics_handles_non_iterable_response() -> None:
    storage = AsyncMock()
    storage.list_epics.return_value = Ellipsis

    use_case = ListEpicsUseCase(storage=storage)
    result = await use_case.execute()

    assert result == []

