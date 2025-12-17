from __future__ import annotations

from typing import Any

import asyncio
import types

import pytest

import services.ray_executor.server as server_module


def test_load_pip_packages_returns_empty_when_file_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr(server_module.os.path, "exists", lambda _: False)

    # Act
    result = server_module._load_pip_packages("/nonexistent/requirements.txt")

    # Assert
    assert result == []


def test_init_ray_connection_uses_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_load_pip(path: str) -> list[str]:  # type: ignore[override]
        calls["path"] = path
        return ["foo", "bar"]

    class _FakeRay:
        def __init__(self) -> None:
            self.args: dict[str, Any] | None = None

        def init(self, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
            self.args = kwargs

    fake_ray = _FakeRay()

    monkeypatch.setattr(server_module, "_load_pip_packages", fake_load_pip)
    monkeypatch.setattr(server_module, "ray", fake_ray)

    # Act
    server_module._init_ray_connection("ray://example:10001")

    # Assert
    assert calls["path"] == "/app/requirements.txt"
    assert fake_ray.args is not None
    assert fake_ray.args["address"] == "ray://example:10001"
    assert fake_ray.args["runtime_env"]["working_dir"] == "/app"
    assert fake_ray.args["runtime_env"]["pip"] == ["foo", "bar"]
    assert fake_ray.args["runtime_env"]["env_vars"]["PYTHONPATH"] == ".:./core"


@pytest.mark.asyncio
async def test_init_nats_connection_disabled_returns_none() -> None:
    client, jetstream = await server_module._init_nats_connection("nats://example:4222", False)

    assert client is None
    assert jetstream is None


@pytest.mark.asyncio
async def test_init_nats_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeClient:
        def __init__(self) -> None:
            self.url: str | None = None

        async def jetstream(self) -> str:  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)  # Make function properly async
            return "js"

    recorded: dict[str, Any] = {}

    async def fake_connect(url: str) -> _FakeClient:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)  # Make function properly async
        recorded["url"] = url
        client = _FakeClient()
        client.url = url
        return client

    monkeypatch.setattr(server_module.nats, "connect", fake_connect)

    client, jetstream = await server_module._init_nats_connection("nats://example:4222", True)

    assert recorded["url"] == "nats://example:4222"
    assert client is not None
    # For our fake client, jetstream is the coroutine; we just assert it exists
    assert jetstream is not None


def test_create_shared_state_structure() -> None:
    start_time, stats, registry = server_module._create_shared_state()

    assert isinstance(start_time, float)
    assert stats["total_deliberations"] == 0
    assert stats["execution_times"] == []
    assert isinstance(registry, dict)


def test_build_use_cases_and_servicer_wires_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    # We only care that it constructs a servicer and returns a status use case
    stats_tracker: dict[str, Any] = {"start_time": 123.0}
    registry: dict[str, Any] = {}

    # Use real adapters, but stub out heavy behavior if needed
    servicer, status_usecase = server_module._build_use_cases_and_servicer(
        stats_tracker=stats_tracker,
        deliberations_registry=registry,
        jetstream=None,
    )

    assert servicer is not None
    assert status_usecase is not None


@pytest.mark.asyncio
async def test_poll_deliberations_handles_empty_registry() -> None:
    class _FakeStatusUseCase:
        async def execute(self, deliberation_id: str) -> Any:  # type: ignore[no-untyped-def]
            raise AssertionError("Should not be called for empty registry")

    registry: dict[str, Any] = {}

    # Save task in variable to prevent premature garbage collection
    task: asyncio.Task[object] = asyncio.create_task(
        server_module._poll_deliberations(
            deliberations_registry=registry,
            get_deliberation_status_usecase=_FakeStatusUseCase(),  # type: ignore[arg-type]
            poll_interval=0.01,
        ),
    )

    await asyncio.sleep(0.03)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_poll_deliberations_processes_running_deliberations(monkeypatch: pytest.MonkeyPatch) -> None:
    """_poll_deliberations should call status use case for running deliberations."""

    class _FakeStatusResponse:
        def __init__(self, status: str) -> None:
            self.status = status
            self.error_message: str | None = None

    class _FakeStatusUseCase:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def execute(self, deliberation_id: str) -> _FakeStatusResponse:  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)  # Make function properly async
            self.calls.append(deliberation_id)
            # Simulate running status so _process_active_deliberations logs nothing special
            return _FakeStatusResponse(status="running")

    registry: dict[str, Any] = {
        "delib-1": {"status": "running"},
        "delib-2": {"status": "completed"},
    }

    usecase = _FakeStatusUseCase()

    # Save task in variable to prevent premature garbage collection
    task: asyncio.Task[object] = asyncio.create_task(
        server_module._poll_deliberations(
            deliberations_registry=registry,
            get_deliberation_status_usecase=usecase,  # type: ignore[arg-type]
            poll_interval=0.01,
        ),
    )

    await asyncio.sleep(0.03)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Only running deliberations should be processed
    assert "delib-1" in usecase.calls
    assert "delib-2" not in usecase.calls


@pytest.mark.asyncio
async def test_process_active_deliberations_handles_completed_and_failed() -> None:
    """_process_active_deliberations should handle completed and failed statuses."""

    class _FakeResponse:
        def __init__(self, status: str, error_message: str | None = None) -> None:
            self.status = status
            self.error_message = error_message

    class _FakeStatusUseCase:
        def __init__(self) -> None:
            self.responses: dict[str, _FakeResponse] = {}

        async def execute(self, deliberation_id: str) -> _FakeResponse:  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)  # Make function properly async
            return self.responses[deliberation_id]

    usecase = _FakeStatusUseCase()
    usecase.responses = {
        "delib-completed": _FakeResponse(status="completed"),
        "delib-failed": _FakeResponse(status="failed", error_message="boom"),
    }

    active = [
        ("delib-completed", {"status": "running"}),
        ("delib-failed", {"status": "running"}),
    ]

    # Just ensure it runs without raising; logging is side-effect only
    await server_module._process_active_deliberations(
        active_deliberations=active,
        get_deliberation_status_usecase=usecase,  # type: ignore[arg-type]
    )
