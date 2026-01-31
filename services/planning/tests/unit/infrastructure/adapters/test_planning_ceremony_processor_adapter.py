"""Unit tests for PlanningCeremonyProcessorAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorError,
)
from planning.infrastructure.adapters.planning_ceremony_processor_adapter import (
    PlanningCeremonyProcessorAdapter,
)


def test_init_rejects_empty_address():
    """Constructor raises ValueError when grpc_address is empty."""
    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        PlanningCeremonyProcessorAdapter(grpc_address="")


def test_init_rejects_whitespace_only_address():
    """Constructor raises ValueError when grpc_address is whitespace only."""
    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        PlanningCeremonyProcessorAdapter(grpc_address="   ")


@patch(
    "planning.infrastructure.adapters.planning_ceremony_processor_adapter.planning_ceremony_pb2_grpc"
)
@patch(
    "planning.infrastructure.adapters.planning_ceremony_processor_adapter.grpc.aio.insecure_channel"
)
def test_init_success(mock_channel, mock_grpc_module):
    """Constructor creates channel and stub with valid address."""
    mock_channel.return_value = MagicMock()
    mock_stub = MagicMock()
    mock_grpc_module.PlanningCeremonyProcessorStub.return_value = mock_stub

    adapter = PlanningCeremonyProcessorAdapter(grpc_address="localhost:50060")

    mock_channel.assert_called_once_with("localhost:50060")
    mock_grpc_module.PlanningCeremonyProcessorStub.assert_called_once_with(
        mock_channel.return_value
    )
    assert adapter._address == "localhost:50060"
    assert adapter._stub == mock_stub


@pytest.mark.asyncio
async def test_start_planning_ceremony_success():
    """start_planning_ceremony returns instance_id from response."""
    mock_stub = MagicMock()
    mock_stub.StartPlanningCeremony = AsyncMock(
        return_value=MagicMock(instance_id="inst-123")
    )
    with patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.grpc.aio.insecure_channel",
        return_value=MagicMock(),
    ), patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub",
        return_value=mock_stub,
    ):
        adapter = PlanningCeremonyProcessorAdapter(grpc_address="localhost:50060")

    result = await adapter.start_planning_ceremony(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        step_ids=("step1",),
        requested_by="user",
        correlation_id="corr-1",
        inputs={"k": "v"},
    )

    assert result == "inst-123"
    mock_stub.StartPlanningCeremony.assert_awaited_once()
    call_arg = mock_stub.StartPlanningCeremony.call_args[0][0]
    assert call_arg.ceremony_id == "c-1"
    assert call_arg.definition_name == "dummy"
    assert call_arg.story_id == "story-1"
    assert list(call_arg.step_ids) == ["step1"]
    assert call_arg.requested_by == "user"
    assert call_arg.correlation_id == "corr-1"
    assert dict(call_arg.inputs) == {"k": "v"}


@pytest.mark.asyncio
async def test_start_planning_ceremony_empty_instance_id_returns_fallback():
    """When response instance_id is empty, returns ceremony_id:story_id."""
    mock_stub = MagicMock()
    mock_stub.StartPlanningCeremony = AsyncMock(
        return_value=MagicMock(instance_id="")
    )
    with patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.grpc.aio.insecure_channel",
        return_value=MagicMock(),
    ), patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub",
        return_value=mock_stub,
    ):
        adapter = PlanningCeremonyProcessorAdapter(grpc_address="localhost:50060")

    result = await adapter.start_planning_ceremony(
        ceremony_id="c-1",
        definition_name="dummy",
        story_id="story-1",
        step_ids=("step1",),
        requested_by="user",
    )

    assert result == "c-1:story-1"


class _FakeRpcError(grpc.RpcError):
    """Minimal RpcError for tests."""

    def __init__(self, details_text: str) -> None:
        self._details = details_text

    def details(self) -> str:
        return self._details


@pytest.mark.asyncio
async def test_start_planning_ceremony_rpc_error_raises():
    """gRPC RpcError is wrapped in PlanningCeremonyProcessorError."""
    mock_stub = MagicMock()
    mock_stub.StartPlanningCeremony = AsyncMock(
        side_effect=_FakeRpcError("unavailable")
    )
    with patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.grpc.aio.insecure_channel",
        return_value=MagicMock(),
    ), patch(
        "planning.infrastructure.adapters.planning_ceremony_processor_adapter.planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub",
        return_value=mock_stub,
    ):
        adapter = PlanningCeremonyProcessorAdapter(grpc_address="localhost:50060")

    with pytest.raises(PlanningCeremonyProcessorError) as exc_info:
        await adapter.start_planning_ceremony(
            ceremony_id="c-1",
            definition_name="dummy",
            story_id="story-1",
            step_ids=("step1",),
            requested_by="user",
        )
    assert "gRPC failed" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None
