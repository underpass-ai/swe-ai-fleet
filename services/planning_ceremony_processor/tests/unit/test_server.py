"""Tests for planning ceremony processor server."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.planning_ceremony_processor import server as server_module


@pytest.mark.asyncio
async def test_serve_requires_protobuf_stubs(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "planning_ceremony_pb2_grpc", None)

    with pytest.raises(RuntimeError, match="protobuf stubs not available"):
        await server_module._serve()


def test_main_invokes_asyncio_run(monkeypatch) -> None:
    called = {"value": False}
    real_run = asyncio.run

    async def _fake_serve() -> None:
        pass

    def _fake_run(coro: object) -> None:
        called["value"] = True
        real_run(coro)  # type: ignore[arg-type]

    monkeypatch.setattr(server_module.asyncio, "run", _fake_run)
    monkeypatch.setattr(server_module, "_serve", _fake_serve)

    server_module.main()

    assert called["value"] is True


@pytest.mark.asyncio
async def test_serve_bootstrap_and_shutdown(monkeypatch) -> None:
    """Run _serve with mocked NATS, gRPC, and adapters; stop_event triggers immediately."""
    mock_grpc_module = MagicMock()
    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.stop = AsyncMock()
    mock_server.add_insecure_port = MagicMock()
    mock_grpc_module.aio.server.return_value = mock_server
    monkeypatch.setattr(server_module, "grpc", mock_grpc_module)
    monkeypatch.setattr(server_module, "planning_ceremony_pb2_grpc", mock_grpc_module)

    mock_nc = AsyncMock()
    mock_nc.connect = AsyncMock()
    mock_nc.close = AsyncMock()
    mock_js = MagicMock()
    mock_sub = MagicMock()
    mock_sub.fetch = AsyncMock(return_value=[])
    mock_js.pull_subscribe = AsyncMock(return_value=mock_sub)
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nats = MagicMock(return_value=mock_nc)
    monkeypatch.setattr(server_module, "NATS", mock_nats)

    mock_config = MagicMock()
    mock_config.nats_url = "nats://test:4222"
    mock_config.ray_executor_url = "ray-executor:50056"
    mock_config.vllm_url = "http://vllm"
    mock_config.vllm_model = "model"
    mock_config.ceremonies_dir = "/app/ceremonies"
    mock_config.valkey_host = "valkey"
    mock_config.valkey_port = 6379
    mock_config.valkey_db = 0
    monkeypatch.setattr(server_module.EnvironmentConfig, "from_env", lambda: mock_config)

    monkeypatch.setattr(server_module, "CeremonyDefinitionAdapter", MagicMock())
    monkeypatch.setattr(server_module, "RayExecutorAdapter", MagicMock())
    monkeypatch.setattr(server_module, "DualPersistenceAdapter", MagicMock())
    monkeypatch.setattr(server_module, "ValkeyIdempotencyAdapter", MagicMock())
    monkeypatch.setattr(server_module, "NATSMessagingAdapter", MagicMock())
    monkeypatch.setattr(server_module, "StepHandlerRegistry", MagicMock())
    monkeypatch.setattr(server_module, "StartPlanningCeremonyUseCase", MagicMock())
    monkeypatch.setattr(
        server_module, "PlanningCeremonyProcessorServicer", MagicMock()
    )

    stop_event = asyncio.Event()
    stop_event.set()

    def _event_factory() -> asyncio.Event:
        return stop_event

    monkeypatch.setattr(server_module.asyncio, "Event", _event_factory)
    monkeypatch.setattr(server_module.signal, "signal", MagicMock())

    ray_close = AsyncMock()
    persistence_close = MagicMock()
    monkeypatch.setattr(
        server_module.RayExecutorAdapter.return_value,
        "close",
        ray_close,
    )
    monkeypatch.setattr(
        server_module.DualPersistenceAdapter.return_value,
        "close",
        persistence_close,
    )
    monkeypatch.setattr(
        server_module.ValkeyIdempotencyAdapter.return_value,
        "close",
        persistence_close,
    )

    await server_module._serve()

    mock_nc.connect.assert_awaited_once()
    mock_server.start.assert_awaited_once()
    mock_server.stop.assert_awaited_once_with(grace=5)
    ray_close.assert_awaited_once()
    assert persistence_close.call_count >= 1
    mock_nc.close.assert_awaited_once()
