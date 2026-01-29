"""Tests for start_planning_ceremony_handler."""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.start_planning_ceremony_via_processor_usecase import (
    StartPlanningCeremonyViaProcessorUseCase,
)
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.start_planning_ceremony_handler import (
    start_planning_ceremony_handler,
)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return MagicMock()


@pytest.mark.asyncio
async def test_start_planning_ceremony_not_configured(mock_context):
    """When use_case is None, returns FAILED_PRECONDITION."""
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy_ceremony",
        story_id="story-1",
        requested_by="user",
        step_ids=["process_step"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=None
    )
    assert response.instance_id == ""
    assert response.message == "Planning Ceremony Processor not configured"
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_start_planning_ceremony_success(mock_context):
    """When use_case is set and request valid, forwards to processor and returns response."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(return_value="instance-123")
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy_ceremony",
        story_id="story-1",
        requested_by="user",
        step_ids=["process_step"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert response.instance_id == "instance-123"
    assert response.status == "accepted"
    assert "started" in response.message.lower()
    use_case.execute.assert_awaited_once()
    call_kw = use_case.execute.call_args.kwargs
    assert call_kw["ceremony_id"] == "c-1"
    assert call_kw["definition_name"] == "dummy_ceremony"
    assert call_kw["story_id"] == "story-1"
    assert call_kw["requested_by"] == "user"
    assert call_kw["step_ids"] == ("process_step",)


@pytest.mark.asyncio
async def test_start_planning_ceremony_validation_ceremony_id(mock_context):
    """Missing ceremony_id returns INVALID_ARGUMENT."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="",
        definition_name="dummy_ceremony",
        story_id="story-1",
        requested_by="user",
        step_ids=["process_step"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert response.instance_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_planning_ceremony_validation_step_ids_empty(mock_context):
    """Empty step_ids returns INVALID_ARGUMENT."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy_ceremony",
        story_id="story-1",
        requested_by="user",
        step_ids=[],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_planning_ceremony_processor_error(mock_context):
    """PlanningCeremonyProcessorError returns UNAVAILABLE."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(
        side_effect=PlanningCeremonyProcessorError("processor unavailable")
    )
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy_ceremony",
        story_id="story-1",
        requested_by="user",
        step_ids=["process_step"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert response.instance_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)


@pytest.mark.asyncio
async def test_start_planning_ceremony_validation_definition_name(mock_context):
    """Missing definition_name returns INVALID_ARGUMENT."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="",
        story_id="story-1",
        requested_by="user",
        step_ids=["step1"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert "definition_name" in response.message.lower()
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_planning_ceremony_validation_story_id(mock_context):
    """Missing story_id returns INVALID_ARGUMENT."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="",
        requested_by="user",
        step_ids=["step1"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert "story_id" in response.message.lower()
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_planning_ceremony_validation_requested_by(mock_context):
    """Missing requested_by returns INVALID_ARGUMENT."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        requested_by="",
        step_ids=["step1"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert "requested_by" in response.message.lower()
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_planning_ceremony_success_with_correlation_id_and_inputs(
    mock_context,
):
    """Success path with correlation_id and inputs forwards them to use case."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(return_value="inst-456")
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        requested_by="user",
        step_ids=["step1"],
        correlation_id="corr-99",
        inputs={"key": "value"},
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert response.instance_id == "inst-456"
    call_kw = use_case.execute.call_args.kwargs
    assert call_kw["correlation_id"] == "corr-99"
    assert call_kw["inputs"] == {"key": "value"}


@pytest.mark.asyncio
async def test_start_planning_ceremony_internal_error(mock_context):
    """Generic Exception returns INTERNAL."""
    use_case = AsyncMock(spec=StartPlanningCeremonyViaProcessorUseCase)
    use_case.execute = AsyncMock(side_effect=RuntimeError("unexpected"))
    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        requested_by="user",
        step_ids=["step1"],
    )
    response = await start_planning_ceremony_handler(
        request, mock_context, use_case=use_case
    )
    assert response.instance_id == ""
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
