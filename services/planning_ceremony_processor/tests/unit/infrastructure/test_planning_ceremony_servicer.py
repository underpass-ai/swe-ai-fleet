"""Tests for PlanningCeremonyProcessorServicer."""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from services.planning_ceremony_processor.infrastructure.grpc import planning_ceremony_servicer as servicer_module


def _make_request(
    ceremony_id: str = "cer-1",
    definition_name: str = "planning_ceremony",
    story_id: str = "story-1",
    correlation_id: str = "",
    inputs: dict | None = None,
    step_ids: list | None = None,
    requested_by: str = "product_owner",
) -> object:
    return type(
        "Request",
        (),
        {
            "ceremony_id": ceremony_id,
            "definition_name": definition_name,
            "story_id": story_id,
            "correlation_id": correlation_id,
            "inputs": inputs if inputs is not None else {},
            "step_ids": step_ids if step_ids is not None else ["submit_architect"],
            "requested_by": requested_by,
        },
    )()


class _DummyResponse:
    def __init__(self, instance_id: str = "", status: str = "", message: str = "") -> None:
        self.instance_id = instance_id
        self.status = status
        self.message = message


class _DummyPb2Module:
    StartPlanningCeremonyResponse = _DummyResponse


class _DummyPb2GrpcModule:
    class PlanningCeremonyProcessorServicer:
        pass


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    use_case = AsyncMock()
    use_case.execute.return_value = type("Instance", (), {"instance_id": "inst-1"})()
    servicer = servicer_module.PlanningCeremonyProcessorServicer(use_case)

    request = _make_request()
    context = MagicMock()

    response = await servicer.StartPlanningCeremony(request, context)

    assert response.instance_id == "inst-1"
    assert response.status == "accepted"
    assert response.message == "ceremony execution started"


def test_planning_ceremony_servicer_rejects_none_use_case(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    with pytest.raises(ValueError, match="use_case is required"):
        servicer_module.PlanningCeremonyProcessorServicer(None)  # type: ignore[arg-type]


def test_planning_ceremony_servicer_requires_protobuf_stubs(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", None)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", None)
    use_case = AsyncMock()

    with pytest.raises(RuntimeError, match="protobuf stubs not available"):
        servicer_module.PlanningCeremonyProcessorServicer(use_case)


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_value_error_returns_invalid_argument(
    monkeypatch,
) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    use_case = AsyncMock()
    use_case.execute.side_effect = ValueError("invalid request")
    servicer = servicer_module.PlanningCeremonyProcessorServicer(use_case)

    request = _make_request()
    context = MagicMock()

    response = await servicer.StartPlanningCeremony(request, context)

    assert response.instance_id == ""
    assert response.status == ""
    assert response.message == ""
    context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    context.set_details.assert_called_once_with("invalid request")


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_generic_exception_returns_internal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    use_case = AsyncMock()
    use_case.execute.side_effect = RuntimeError("internal error")
    servicer = servicer_module.PlanningCeremonyProcessorServicer(use_case)

    request = _make_request()
    context = MagicMock()

    response = await servicer.StartPlanningCeremony(request, context)

    assert response.instance_id == ""
    assert response.status == ""
    assert response.message == ""
    context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
    context.set_details.assert_called_once_with("internal error")


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_passes_correlation_id_none_when_empty(
    monkeypatch,
) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    use_case = AsyncMock()
    instance = type("Instance", (), {"instance_id": "inst-2"})()
    use_case.execute.return_value = instance
    servicer = servicer_module.PlanningCeremonyProcessorServicer(use_case)

    request = _make_request(correlation_id="")
    context = MagicMock()

    await servicer.StartPlanningCeremony(request, context)

    call_args = use_case.execute.call_args[0][0]
    assert call_args.correlation_id is None
