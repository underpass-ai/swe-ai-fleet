"""Tests for RayExecutorAdapter."""

import types

import pytest

from services.planning_ceremony_processor.infrastructure.adapters import ray_executor_adapter as adapter_module


class _DummyResponse:
    def __init__(self, deliberation_id: str) -> None:
        self.deliberation_id = deliberation_id


class _DummyStub:
    def __init__(self, _channel) -> None:
        pass

    async def ExecuteBacklogReviewDeliberation(self, _request):
        return _DummyResponse("delib-1")

    async def ExecuteDeliberation(self, _request):
        return _DummyResponse("delib-2")


class _DummyGrpcModule:
    class RayExecutorServiceStub:  # noqa: D401 - external signature
        def __init__(self, channel) -> None:
            self._stub = _DummyStub(channel)

        async def ExecuteBacklogReviewDeliberation(self, request):
            return await self._stub.ExecuteBacklogReviewDeliberation(request)

        async def ExecuteDeliberation(self, request):
            return await self._stub.ExecuteDeliberation(request)


class _DummyPb2Module:
    class Agent:
        def __init__(self, **_kwargs) -> None:
            pass

    class BacklogReviewTaskConstraints:
        def __init__(self, **_kwargs) -> None:
            pass

    class ExecuteBacklogReviewDeliberationRequest:
        def __init__(self, **_kwargs) -> None:
            pass

    class TaskConstraints:
        def __init__(self, **_kwargs) -> None:
            pass

    class ExecuteDeliberationRequest:
        def __init__(self, **_kwargs) -> None:
            pass


@pytest.mark.asyncio
async def test_ray_executor_adapter_submits_deliberation(monkeypatch) -> None:
    monkeypatch.setattr(adapter_module, "ray_executor_pb2", _DummyPb2Module)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _DummyGrpcModule)
    monkeypatch.setattr(
        adapter_module.grpc.aio,
        "insecure_channel",
        lambda _address: types.SimpleNamespace(),
    )

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )

    deliberation_id = await adapter.submit_backlog_review_deliberation(
        task_id="ceremony-1:story-1:role-ARCHITECT",
        task_description="desc",
        role="ARCHITECT",
        story_id="story-1",
        num_agents=1,
        constraints=None,
    )

    assert deliberation_id == "delib-1"


@pytest.mark.asyncio
async def test_ray_executor_adapter_submits_task_extraction(monkeypatch) -> None:
    monkeypatch.setattr(adapter_module, "ray_executor_pb2", _DummyPb2Module)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _DummyGrpcModule)
    monkeypatch.setattr(
        adapter_module.grpc.aio,
        "insecure_channel",
        lambda _address: types.SimpleNamespace(),
    )

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )

    deliberation_id = await adapter.submit_task_extraction(
        task_id="ceremony-1:story-1:task-extraction",
        task_description="prompt",
        story_id="story-1",
        ceremony_id="ceremony-1",
    )

    assert deliberation_id == "delib-2"


@pytest.mark.asyncio
async def test_ray_executor_adapter_rejects_invalid_num_agents(monkeypatch) -> None:
    monkeypatch.setattr(adapter_module, "ray_executor_pb2", _DummyPb2Module)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _DummyGrpcModule)
    monkeypatch.setattr(
        adapter_module.grpc.aio,
        "insecure_channel",
        lambda _address: types.SimpleNamespace(),
    )

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )

    with pytest.raises(ValueError, match="num_agents must be positive"):
        await adapter.submit_backlog_review_deliberation(
            task_id="ceremony-1:story-1:role-ARCHITECT",
            task_description="desc",
            role="ARCHITECT",
            story_id="story-1",
            num_agents=0,
            constraints=None,
        )
