"""Tests for GetPlanningCeremonyViaProcessorUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
)
from planning.application.usecases.get_planning_ceremony_via_processor_usecase import (
    GetPlanningCeremonyViaProcessorUseCase,
)


def test_requires_processor() -> None:
    with pytest.raises(ValueError, match="processor is required"):
        GetPlanningCeremonyViaProcessorUseCase(processor=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_execute_calls_processor() -> None:
    processor = AsyncMock()
    processor.get_planning_ceremony = AsyncMock(
        return_value=PlanningCeremonyInstanceData(
            instance_id="inst-1",
            ceremony_id="cer-1",
            story_id="story-1",
            definition_name="dummy_ceremony",
            current_state="in_progress",
            status="IN_PROGRESS",
            correlation_id="corr-1",
            step_status={},
            step_outputs={},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:01:00+00:00",
        )
    )
    use_case = GetPlanningCeremonyViaProcessorUseCase(processor=processor)

    result = await use_case.execute("inst-1")

    assert result is not None
    assert result.instance_id == "inst-1"
    processor.get_planning_ceremony.assert_awaited_once_with("inst-1")


@pytest.mark.asyncio
async def test_execute_rejects_empty_instance_id() -> None:
    processor = AsyncMock()
    use_case = GetPlanningCeremonyViaProcessorUseCase(processor=processor)

    with pytest.raises(ValueError, match="instance_id is required"):
        await use_case.execute("   ")
