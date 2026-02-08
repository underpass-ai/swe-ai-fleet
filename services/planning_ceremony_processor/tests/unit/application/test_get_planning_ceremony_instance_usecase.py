"""Tests for GetPlanningCeremonyInstanceUseCase."""

from unittest.mock import AsyncMock

import pytest

from services.planning_ceremony_processor.application.usecases.get_planning_ceremony_instance_usecase import (
    GetPlanningCeremonyInstanceUseCase,
)


def test_requires_persistence_port() -> None:
    with pytest.raises(ValueError, match="persistence_port is required"):
        GetPlanningCeremonyInstanceUseCase(persistence_port=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_loads_instance_by_id() -> None:
    persistence = AsyncMock()
    persistence.load_instance = AsyncMock(return_value="instance")
    use_case = GetPlanningCeremonyInstanceUseCase(persistence_port=persistence)

    result = await use_case.execute("inst-1")

    assert result == "instance"
    persistence.load_instance.assert_awaited_once_with("inst-1")


@pytest.mark.asyncio
async def test_rejects_empty_instance_id() -> None:
    persistence = AsyncMock()
    use_case = GetPlanningCeremonyInstanceUseCase(persistence_port=persistence)

    with pytest.raises(ValueError, match="instance_id cannot be empty"):
        await use_case.execute("   ")
