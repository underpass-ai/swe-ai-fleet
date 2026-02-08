"""Tests for ListPlanningCeremonyInstancesUseCase."""

from unittest.mock import AsyncMock

import pytest

from services.planning_ceremony_processor.application.usecases.list_planning_ceremony_instances_usecase import (
    ListPlanningCeremonyInstancesUseCase,
)


def test_requires_persistence_port() -> None:
    with pytest.raises(ValueError, match="persistence_port is required"):
        ListPlanningCeremonyInstancesUseCase(persistence_port=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_lists_instances_with_filters() -> None:
    persistence = AsyncMock()
    persistence.list_instances = AsyncMock(return_value=(["inst"], 1))
    use_case = ListPlanningCeremonyInstancesUseCase(persistence_port=persistence)

    instances, total = await use_case.execute(
        limit=20,
        offset=5,
        state_filter="IN_PROGRESS",
        definition_filter="dummy_ceremony",
        story_id="story-1",
    )

    assert instances == ["inst"]
    assert total == 1
    persistence.list_instances.assert_awaited_once_with(
        limit=20,
        offset=5,
        state_filter="IN_PROGRESS",
        definition_filter="dummy_ceremony",
        story_id="story-1",
    )


@pytest.mark.asyncio
async def test_defaults_pagination_when_invalid() -> None:
    persistence = AsyncMock()
    persistence.list_instances = AsyncMock(return_value=([], 0))
    use_case = ListPlanningCeremonyInstancesUseCase(persistence_port=persistence)

    await use_case.execute(limit=0, offset=-1)

    persistence.list_instances.assert_awaited_once_with(
        limit=100,
        offset=0,
        state_filter=None,
        definition_filter=None,
        story_id=None,
    )
