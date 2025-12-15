from __future__ import annotations

"""Unit tests for the serve() entrypoint in server.py."""

from typing import Any

import asyncio
import types

import pytest

import services.ray_executor.server as server_module


@pytest.mark.asyncio
async def test_serve_initializes_and_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """serve should initialize server components and handle KeyboardInterrupt shutdown."""

    # Fake config
    class _FakeConfig:
        def __init__(self) -> None:
            self.port = 50056
            self.ray_address = "ray://example:10001"
            self.nats_url = "nats://example:4222"
            self.enable_nats = False

    # Avoid real ray/nats connections
    monkeypatch.setattr(server_module, "_init_ray_connection", lambda addr: None)
    async def _fake_init_nats(url: str, enable: bool) -> tuple[None, None]:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)  # Make function properly async
        return None, None
    monkeypatch.setattr(server_module, "_init_nats_connection", _fake_init_nats)

    # Fake gRPC server
    class _FakeServer:
        def __init__(self) -> None:
            self.started = False
            self.stopped = False
            self.ports: list[str] = []

        def add_insecure_port(self, addr: str) -> None:  # type: ignore[no-untyped-def]
            self.ports.append(addr)

        async def start(self) -> None:  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)  # Make function properly async
            self.started = True

        async def wait_for_termination(self) -> None:  # type: ignore[no-untyped-def]
            # Simulate Ctrl+C to exercise shutdown path
            raise KeyboardInterrupt()

        async def stop(self, grace: float) -> None:  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)  # Make function properly async
            self.stopped = True

    fake_server = _FakeServer()

    class _FakeGrpcAio:
        def server(self) -> _FakeServer:  # type: ignore[no-untyped-def]
            return fake_server

    monkeypatch.setattr(server_module, "grpc_aio", _FakeGrpcAio())

    # Avoid real ray and nats shutdown
    monkeypatch.setattr(server_module, "ray", types.SimpleNamespace(shutdown=lambda: None))

    # Fake add_RayExecutorServiceServicer_to_server to avoid import-time side effects
    class _FakePb2Grpc:
        @staticmethod
        def add_RayExecutorServiceServicer_to_server(servicer: Any, server: Any) -> None:  # type: ignore[no-untyped-def]  # noqa: N802  # NOSONAR - Mocking protobuf-generated interface (must match generated method name)
            # No-op: we only care that it's called without error
            return None

    monkeypatch.setattr(server_module, "ray_executor_pb2_grpc", _FakePb2Grpc())

    # Fake config loader
    monkeypatch.setattr(server_module, "load_ray_executor_config", lambda: _FakeConfig())

    # Track polling task to ensure it's cancelled
    created_tasks: list[asyncio.Task[Any]] = []

    original_create_task = asyncio.create_task

    def _tracking_create_task(coro: Any) -> asyncio.Task[Any]:  # type: ignore[no-untyped-def]
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", _tracking_create_task)

    # Run serve; it should exit after simulated KeyboardInterrupt
    await server_module.serve()

    # Assertions: server started and stopped, polling task cancelled
    assert fake_server.started is True
    assert fake_server.stopped is True
    assert any(task.cancelled() or task.done() for task in created_tasks)

