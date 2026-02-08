"""Tests for PlanningCeremonyProcessorServicer."""

from datetime import datetime, timezone
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


class _DummyGetResponse:
    def __init__(
        self,
        ceremony: object | None = None,
        success: bool = False,
        message: str = "",
    ) -> None:
        self.ceremony = ceremony
        self.success = success
        self.message = message


class _DummyListResponse:
    def __init__(
        self,
        ceremonies: list | None = None,
        total_count: int = 0,
        success: bool = False,
        message: str = "",
    ) -> None:
        self.ceremonies = ceremonies if ceremonies is not None else []
        self.total_count = total_count
        self.success = success
        self.message = message


class _DummyPlanningCeremonyInstance:
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class _DummyPb2Module:
    StartPlanningCeremonyResponse = _DummyResponse
    GetPlanningCeremonyInstanceResponse = _DummyGetResponse
    ListPlanningCeremonyInstancesResponse = _DummyListResponse
    PlanningCeremonyInstance = _DummyPlanningCeremonyInstance


class _DummyPb2GrpcModule:
    class PlanningCeremonyProcessorServicer:
        pass


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    start_use_case = AsyncMock()
    start_use_case.execute.return_value = type("Instance", (), {"instance_id": "inst-1"})()
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()
    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )

    request = _make_request()
    context = MagicMock()

    response = await servicer.StartPlanningCeremony(request, context)

    assert response.instance_id == "inst-1"
    assert response.status == "accepted"
    assert response.message == "ceremony execution started"


def test_planning_ceremony_servicer_rejects_none_use_case(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)
    start_use_case = AsyncMock()
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()

    with pytest.raises(ValueError, match="start_use_case is required"):
        servicer_module.PlanningCeremonyProcessorServicer(None, get_use_case, list_use_case)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="get_use_case is required"):
        servicer_module.PlanningCeremonyProcessorServicer(start_use_case, None, list_use_case)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="list_use_case is required"):
        servicer_module.PlanningCeremonyProcessorServicer(start_use_case, get_use_case, None)  # type: ignore[arg-type]


def test_planning_ceremony_servicer_requires_protobuf_stubs(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", None)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", None)
    start_use_case = AsyncMock()
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()

    with pytest.raises(RuntimeError, match="protobuf stubs not available"):
        servicer_module.PlanningCeremonyProcessorServicer(
            start_use_case, get_use_case, list_use_case
        )


@pytest.mark.asyncio
async def test_planning_ceremony_servicer_value_error_returns_invalid_argument(
    monkeypatch,
) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    start_use_case = AsyncMock()
    start_use_case.execute.side_effect = ValueError("invalid request")
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()
    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )

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

    start_use_case = AsyncMock()
    start_use_case.execute.side_effect = RuntimeError("internal error")
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()
    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )

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

    start_use_case = AsyncMock()
    instance = type("Instance", (), {"instance_id": "inst-2"})()
    start_use_case.execute.return_value = instance
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()
    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )

    request = _make_request(correlation_id="")
    context = MagicMock()

    await servicer.StartPlanningCeremony(request, context)

    call_args = start_use_case.execute.call_args[0][0]
    assert call_args.correlation_id is None


@pytest.mark.asyncio
async def test_get_planning_ceremony_instance_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    start_use_case = AsyncMock()
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()
    instance = MagicMock()
    instance.instance_id = "cer-1:story-1"
    instance.definition.name = "dummy_ceremony"
    instance.current_state = "in_progress"
    instance.correlation_id = "corr-1"
    instance.step_status.entries = ()
    instance.step_outputs.entries = ()
    instance.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instance.updated_at = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    instance.is_terminal.return_value = False
    instance.is_completed.return_value = False
    get_use_case.execute.return_value = instance

    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )
    request = type("Request", (), {"instance_id": "cer-1:story-1"})()
    context = MagicMock()

    response = await servicer.GetPlanningCeremonyInstance(request, context)

    assert response.success is True
    assert response.ceremony.instance_id == "cer-1:story-1"
    assert response.ceremony.story_id == "story-1"
    assert response.ceremony.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_get_planning_ceremony_instance_missing_id(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        AsyncMock(), AsyncMock(), AsyncMock()
    )
    request = type("Request", (), {"instance_id": ""})()
    context = MagicMock()

    response = await servicer.GetPlanningCeremonyInstance(request, context)

    assert response.success is False
    context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_list_planning_ceremony_instances_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2", _DummyPb2Module)
    monkeypatch.setattr(servicer_module, "planning_ceremony_pb2_grpc", _DummyPb2GrpcModule)

    start_use_case = AsyncMock()
    get_use_case = AsyncMock()
    list_use_case = AsyncMock()

    instance = MagicMock()
    instance.instance_id = "cer-1:story-1"
    instance.definition.name = "dummy_ceremony"
    instance.current_state = "done"
    instance.correlation_id = "corr-1"
    instance.step_status.entries = ()
    instance.step_outputs.entries = ()
    instance.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instance.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instance.is_terminal.return_value = True
    instance.is_completed.return_value = True

    list_use_case.execute.return_value = ([instance], 1)
    servicer = servicer_module.PlanningCeremonyProcessorServicer(
        start_use_case, get_use_case, list_use_case
    )
    request = type(
        "Request",
        (),
        {
            "limit": 20,
            "offset": 0,
            "state_filter": "COMPLETED",
            "definition_filter": "",
            "story_id": "",
            "HasField": lambda self, name: name == "state_filter",
        },
    )()
    context = MagicMock()

    response = await servicer.ListPlanningCeremonyInstances(request, context)

    assert response.success is True
    assert response.total_count == 1
    assert len(response.ceremonies) == 1
    assert response.ceremonies[0].status == "COMPLETED"
