"""Unit tests for StartPlanningCeremonyViaProcessorUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorPort,
)
from planning.application.usecases.start_planning_ceremony_via_processor_usecase import (
    StartPlanningCeremonyViaProcessorUseCase,
)


def test_post_init_rejects_none_processor():
    """Constructor raises ValueError when processor is None."""
    with pytest.raises(ValueError, match="processor is required"):
        StartPlanningCeremonyViaProcessorUseCase(processor=None)


@pytest.mark.asyncio
async def test_execute_forwards_to_processor():
    """execute calls processor.start_planning_ceremony with given args."""
    processor = AsyncMock(spec=PlanningCeremonyProcessorPort)
    processor.start_planning_ceremony = AsyncMock(return_value="inst-1")
    use_case = StartPlanningCeremonyViaProcessorUseCase(processor=processor)

    result = await use_case.execute(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        step_ids=("step1", "step2"),
        requested_by="user",
        correlation_id="corr-1",
        inputs={"k": "v"},
    )

    assert result == "inst-1"
    processor.start_planning_ceremony.assert_awaited_once_with(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        step_ids=("step1", "step2"),
        requested_by="user",
        correlation_id="corr-1",
        inputs={"k": "v"},
    )


@pytest.mark.asyncio
async def test_execute_forwards_none_correlation_id_and_inputs():
    """execute passes None correlation_id and inputs when not provided."""
    processor = AsyncMock(spec=PlanningCeremonyProcessorPort)
    processor.start_planning_ceremony = AsyncMock(return_value="inst-2")
    use_case = StartPlanningCeremonyViaProcessorUseCase(processor=processor)

    await use_case.execute(
        ceremony_id="c-2",
        definition_name="def",
        story_id="s-2",
        step_ids=("step1",),
        requested_by="po",
        correlation_id=None,
        inputs=None,
    )

    processor.start_planning_ceremony.assert_awaited_once_with(
        ceremony_id="c-2",
        definition_name="def",
        story_id="s-2",
        step_ids=("step1",),
        requested_by="po",
        correlation_id=None,
        inputs=None,
    )


@pytest.mark.asyncio
async def test_execute_propagates_processor_error():
    """execute propagates PlanningCeremonyProcessorError from processor."""
    from planning.application.ports.planning_ceremony_processor_port import (
        PlanningCeremonyProcessorError,
    )

    processor = AsyncMock(spec=PlanningCeremonyProcessorPort)
    processor.start_planning_ceremony = AsyncMock(
        side_effect=PlanningCeremonyProcessorError("gRPC failed")
    )
    use_case = StartPlanningCeremonyViaProcessorUseCase(processor=processor)

    with pytest.raises(PlanningCeremonyProcessorError, match="gRPC failed"):
        await use_case.execute(
            ceremony_id="c-1",
            definition_name="dummy",
            story_id="story-1",
            step_ids=("step1",),
            requested_by="user",
        )
