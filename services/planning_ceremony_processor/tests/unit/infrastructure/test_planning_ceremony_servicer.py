"""Tests for PlanningCeremonyProcessorServicer."""

from unittest.mock import AsyncMock

import pytest

from services.planning_ceremony_processor.infrastructure.grpc import planning_ceremony_servicer as servicer_module


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

    request = type(
        "Request",
        (),
        {
            "ceremony_id": "cer-1",
            "definition_name": "planning_ceremony",
            "story_id": "story-1",
            "correlation_id": "",
            "inputs": {},
            "step_ids": ["submit_architect"],
            "requested_by": "product_owner",
        },
    )()
    context = AsyncMock()

    response = await servicer.StartPlanningCeremony(request, context)

    assert response.instance_id == "inst-1"
    assert response.status == "accepted"
    assert response.message == "ceremony execution started"
