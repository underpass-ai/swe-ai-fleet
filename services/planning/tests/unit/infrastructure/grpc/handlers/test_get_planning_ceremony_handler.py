"""Tests for get_planning_ceremony_handler."""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.get_planning_ceremony_via_processor_usecase import (
    GetPlanningCeremonyViaProcessorUseCase,
)
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.get_planning_ceremony_handler import (
    get_planning_ceremony_handler,
)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return MagicMock()


@pytest.mark.asyncio
async def test_get_planning_ceremony_not_configured(mock_context):
    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="inst-1")
    response = await get_planning_ceremony_handler(request, mock_context, use_case=None)
    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_get_planning_ceremony_validation_instance_id(mock_context):
    use_case = AsyncMock(spec=GetPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="")
    response = await get_planning_ceremony_handler(request, mock_context, use_case=use_case)
    assert response.success is False
    assert "instance_id" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_planning_ceremony_success(mock_context):
    use_case = AsyncMock(spec=GetPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(
        return_value=PlanningCeremonyInstanceData(
            instance_id="cer-1:story-1",
            ceremony_id="cer-1",
            story_id="story-1",
            definition_name="dummy_ceremony",
            current_state="in_progress",
            status="IN_PROGRESS",
            correlation_id="corr-1",
            step_status={"step1": "COMPLETED"},
            step_outputs={"step1": "{\"ok\":true}"},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:01:00+00:00",
        )
    )

    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="cer-1:story-1")
    response = await get_planning_ceremony_handler(request, mock_context, use_case=use_case)

    assert response.success is True
    assert response.ceremony.instance_id == "cer-1:story-1"
    assert response.ceremony.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_get_planning_ceremony_processor_error(mock_context):
    use_case = AsyncMock(spec=GetPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(
        side_effect=PlanningCeremonyProcessorError("processor unavailable")
    )

    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="cer-1:story-1")
    response = await get_planning_ceremony_handler(request, mock_context, use_case=use_case)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)
