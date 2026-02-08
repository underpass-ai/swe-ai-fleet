"""Tests for list_planning_ceremonies_handler."""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.list_planning_ceremonies_via_processor_usecase import (
    ListPlanningCeremoniesViaProcessorUseCase,
)
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.list_planning_ceremonies_handler import (
    list_planning_ceremonies_handler,
)


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.mark.asyncio
async def test_list_planning_ceremonies_not_configured(mock_context):
    request = planning_pb2.ListPlanningCeremoniesRequest(limit=10, offset=0)
    response = await list_planning_ceremonies_handler(request, mock_context, use_case=None)
    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_list_planning_ceremonies_success(mock_context):
    use_case = AsyncMock(spec=ListPlanningCeremoniesViaProcessorUseCase)
    use_case.execute = AsyncMock(
        return_value=(
            [
                PlanningCeremonyInstanceData(
                    instance_id="cer-1:story-1",
                    ceremony_id="cer-1",
                    story_id="story-1",
                    definition_name="dummy_ceremony",
                    current_state="done",
                    status="COMPLETED",
                    correlation_id="corr-1",
                    step_status={"step1": "COMPLETED"},
                    step_outputs={"step1": "{\"ok\":true}"},
                    created_at="2026-01-01T00:00:00+00:00",
                    updated_at="2026-01-01T00:01:00+00:00",
                )
            ],
            1,
        )
    )

    request = planning_pb2.ListPlanningCeremoniesRequest(
        limit=10,
        offset=0,
        state_filter="COMPLETED",
    )
    response = await list_planning_ceremonies_handler(request, mock_context, use_case=use_case)

    assert response.success is True
    assert response.total_count == 1
    assert len(response.ceremonies) == 1
    assert response.ceremonies[0].status == "COMPLETED"
    use_case.execute.assert_awaited_once_with(
        limit=10,
        offset=0,
        state_filter="COMPLETED",
        definition_filter=None,
        story_id=None,
    )


@pytest.mark.asyncio
async def test_list_planning_ceremonies_processor_error(mock_context):
    use_case = AsyncMock(spec=ListPlanningCeremoniesViaProcessorUseCase)
    use_case.execute = AsyncMock(
        side_effect=PlanningCeremonyProcessorError("processor unavailable")
    )

    request = planning_pb2.ListPlanningCeremoniesRequest(limit=10, offset=0)
    response = await list_planning_ceremonies_handler(request, mock_context, use_case=use_case)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)
