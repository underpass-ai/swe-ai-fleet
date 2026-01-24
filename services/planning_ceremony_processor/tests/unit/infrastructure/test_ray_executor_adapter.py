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


def _patch_ray_adapter(monkeypatch) -> None:
    monkeypatch.setattr(adapter_module, "ray_executor_pb2", _DummyPb2Module)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _DummyGrpcModule)
    monkeypatch.setattr(
        adapter_module.grpc.aio,
        "insecure_channel",
        lambda _address: types.SimpleNamespace(),
    )


def test_ray_executor_adapter_rejects_empty_grpc_address(monkeypatch) -> None:
    _patch_ray_adapter(monkeypatch)
    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        adapter_module.RayExecutorAdapter(
            grpc_address="",
            vllm_url="http://vllm",
            vllm_model="model",
        )


def test_ray_executor_adapter_rejects_empty_vllm_url(monkeypatch) -> None:
    _patch_ray_adapter(monkeypatch)
    with pytest.raises(ValueError, match="vllm_url cannot be empty"):
        adapter_module.RayExecutorAdapter(
            grpc_address="ray-executor:50056",
            vllm_url="",
            vllm_model="model",
        )


def test_ray_executor_adapter_rejects_empty_vllm_model(monkeypatch) -> None:
    _patch_ray_adapter(monkeypatch)
    with pytest.raises(ValueError, match="vllm_model cannot be empty"):
        adapter_module.RayExecutorAdapter(
            grpc_address="ray-executor:50056",
            vllm_url="http://vllm",
            vllm_model="",
        )


def test_ray_executor_adapter_requires_protobuf_stubs(monkeypatch) -> None:
    monkeypatch.setattr(adapter_module, "ray_executor_pb2", None)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", None)
    with pytest.raises(RuntimeError, match="protobuf stubs not available"):
        adapter_module.RayExecutorAdapter(
            grpc_address="ray-executor:50056",
            vllm_url="http://vllm",
            vllm_model="model",
        )


@pytest.mark.asyncio
async def test_ray_executor_adapter_submits_deliberation_with_constraints(
    monkeypatch,
) -> None:
    _patch_ray_adapter(monkeypatch)
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
        constraints={"key1": "v1", "key2": 42},
    )
    assert deliberation_id == "delib-1"


@pytest.mark.asyncio
async def test_ray_executor_adapter_deliberation_grpc_error_raises_runtime_error(
    monkeypatch,
) -> None:
    import grpc
    from grpc import aio as grpc_aio

    _patch_ray_adapter(monkeypatch)
    rpc_err = grpc_aio.AioRpcError(
        grpc.StatusCode.INTERNAL, (), (), details="deliberation failed"
    )

    class _FailingStub:
        def __init__(self, _channel) -> None:
            pass

        async def ExecuteBacklogReviewDeliberation(self, _request):
            raise rpc_err

    class _FailingGrpcModule:
        class RayExecutorServiceStub:
            def __init__(self, channel) -> None:
                self._stub = _FailingStub(channel)

            async def ExecuteBacklogReviewDeliberation(self, request):
                return await self._stub.ExecuteBacklogReviewDeliberation(request)

            async def ExecuteDeliberation(self, request):
                return _DummyResponse("delib-2")

    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _FailingGrpcModule)

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )

    with pytest.raises(RuntimeError, match="gRPC error calling Ray Executor"):
        await adapter.submit_backlog_review_deliberation(
            task_id="ceremony-1:story-1:role-ARCHITECT",
            task_description="desc",
            role="ARCHITECT",
            story_id="story-1",
            num_agents=1,
            constraints=None,
        )


@pytest.mark.asyncio
async def test_ray_executor_adapter_task_extraction_grpc_error_raises_runtime_error(
    monkeypatch,
) -> None:
    import grpc
    from grpc import aio as grpc_aio

    _patch_ray_adapter(monkeypatch)
    rpc_err = grpc_aio.AioRpcError(
        grpc.StatusCode.INTERNAL, (), (), details="task extraction failed"
    )

    class _FailingStub:
        def __init__(self, _channel) -> None:
            pass

        async def ExecuteBacklogReviewDeliberation(self, _request):
            return _DummyResponse("delib-1")

        async def ExecuteDeliberation(self, _request):
            raise rpc_err

    class _FailingGrpcModule:
        class RayExecutorServiceStub:
            def __init__(self, channel) -> None:
                self._stub = _FailingStub(channel)

            async def ExecuteBacklogReviewDeliberation(self, request):
                return await self._stub.ExecuteBacklogReviewDeliberation(request)

            async def ExecuteDeliberation(self, request):
                return await self._stub.ExecuteDeliberation(request)

    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _FailingGrpcModule)

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )

    with pytest.raises(RuntimeError, match="gRPC error calling Ray Executor"):
        await adapter.submit_task_extraction(
            task_id="ceremony-1:story-1:task-extraction",
            task_description="prompt",
            story_id="story-1",
            ceremony_id="ceremony-1",
        )


@pytest.mark.asyncio
async def test_ray_executor_adapter_close(monkeypatch) -> None:
    closed = []

    async def _fake_close() -> None:
        closed.append(True)

    fake_channel = types.SimpleNamespace(close=_fake_close)

    monkeypatch.setattr(adapter_module, "ray_executor_pb2", _DummyPb2Module)
    monkeypatch.setattr(adapter_module, "ray_executor_pb2_grpc", _DummyGrpcModule)
    monkeypatch.setattr(
        adapter_module.grpc.aio,
        "insecure_channel",
        lambda _address: fake_channel,
    )

    adapter = adapter_module.RayExecutorAdapter(
        grpc_address="ray-executor:50056",
        vllm_url="http://vllm",
        vllm_model="model",
    )
    await adapter.close()

    assert closed == [True]
