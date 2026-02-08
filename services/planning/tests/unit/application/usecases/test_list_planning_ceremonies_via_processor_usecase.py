"""Tests for ListPlanningCeremoniesViaProcessorUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.list_planning_ceremonies_via_processor_usecase import (
    ListPlanningCeremoniesViaProcessorUseCase,
)


def test_requires_processor() -> None:
    with pytest.raises(ValueError, match="processor is required"):
        ListPlanningCeremoniesViaProcessorUseCase(processor=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_execute_calls_processor_with_sanitized_values() -> None:
    processor = AsyncMock()
    processor.list_planning_ceremonies = AsyncMock(return_value=([], 0))
    use_case = ListPlanningCeremoniesViaProcessorUseCase(processor=processor)

    await use_case.execute(
        limit=0,
        offset=-1,
        state_filter=" COMPLETED ",
        definition_filter=" dummy_ceremony ",
        story_id=" story-1 ",
    )

    processor.list_planning_ceremonies.assert_awaited_once_with(
        limit=100,
        offset=0,
        state_filter="COMPLETED",
        definition_filter="dummy_ceremony",
        story_id="story-1",
    )
