from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from services.ray_executor import server


class TestLoadPipPackages:
    """Unit tests for _load_pip_packages helper."""

    def test_load_pip_packages_returns_empty_when_file_missing(self, tmp_path: Any) -> None:
        # Use a non-existent path under tmp
        missing_path = tmp_path / "does_not_exist.txt"

        result = server._load_pip_packages(str(missing_path))

        assert result == []

    def test_load_pip_packages_parses_non_comment_lines(self, tmp_path: Any) -> None:
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("""# comment line
package-one

package-two==1.0.0
# indented comment
""")

        result = server._load_pip_packages(str(requirements))

        assert result == ["package-one", "package-two==1.0.0"]


class TestInitRayConnection:
    """Unit tests for _init_ray_connection wiring with runtime_env."""

    def test_init_ray_connection_calls_ray_init_with_runtime_env(self, mocker: Any) -> None:
        mock_ray_init = mocker.patch("services.ray_executor.server.ray.init")
        mock_load_pip = mocker.patch(
            "services.ray_executor.server._load_pip_packages",
            return_value=["foo", "bar"],
        )

        server._init_ray_connection("ray://test-cluster")

        mock_load_pip.assert_called_once_with("/app/requirements.txt")
        mock_ray_init.assert_called_once()
        kwargs = mock_ray_init.call_args.kwargs
        assert kwargs["address"] == "ray://test-cluster"
        assert kwargs["ignore_reinit_error"] is True
        runtime_env = kwargs["runtime_env"]
        assert runtime_env["working_dir"] == "/app"
        assert runtime_env["pip"] == ["foo", "bar"]
        assert runtime_env["env_vars"]["PYTHONPATH"] == ".:./core"


class TestInitNatsConnection:
    """Unit tests for _init_nats_connection helper."""

    @pytest.mark.asyncio
    async def test_init_nats_connection_disabled_returns_none_tuple(self, mocker: Any) -> None:
        mock_connect = mocker.patch("services.ray_executor.server.nats.connect")

        nats_client, jetstream = await server._init_nats_connection(
            nats_url="nats://localhost:4222",
            enable_nats=False,
        )

        mock_connect.assert_not_called()
        assert nats_client is None
        assert jetstream is None

    @pytest.mark.asyncio
    async def test_init_nats_connection_enabled_connects_and_returns_client_and_js(self, mocker: Any) -> None:
        mock_nc = mocker.MagicMock()
        mock_js = object()
        mock_nc.jetstream.return_value = mock_js
        mocker.patch("services.ray_executor.server.nats.connect", return_value=mock_nc)

        nats_client, jetstream = await server._init_nats_connection(
            nats_url="nats://localhost:4222",
            enable_nats=True,
        )

        assert nats_client is mock_nc
        assert jetstream is mock_js


class TestCreateSharedState:
    """Unit tests for _create_shared_state helper."""

    def test_create_shared_state_initializes_stats_and_registry(self) -> None:
        start_time, stats_tracker, deliberations_registry = server._create_shared_state()

        assert isinstance(start_time, float)
        assert stats_tracker == {
            "total_deliberations": 0,
            "active_deliberations": 0,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
            "execution_times": [],
        }
        assert deliberations_registry == {}


class TestBuildUseCasesAndServicer:
    """Unit tests for _build_use_cases_and_servicer wiring."""

    def test_build_use_cases_and_servicer_wires_dependencies(self, mocker: Any) -> None:
        stats_tracker: dict[str, Any] = {}
        deliberations_registry: dict[str, Any] = {}
        fake_jetstream = object()

        servicer, get_status_uc = server._build_use_cases_and_servicer(
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
            jetstream=fake_jetstream,
        )

        # Servicer type and attribute presence
        from services.ray_executor.grpc_servicer import RayExecutorServiceServicer

        assert isinstance(servicer, RayExecutorServiceServicer)
        assert get_status_uc is not None


class TestProcessActiveDeliberations:
    """Unit tests for _process_active_deliberations polling logic."""

    @pytest.mark.asyncio
    async def test_process_active_deliberations_logs_completed_and_failed(self, mocker: Any) -> None:
        @dataclass
        class _StatusResponse:
            status: str
            error_message: str | None = None

        class _DummyStatusUseCase:
            def __init__(self) -> None:
                self.calls: list[str] = []

            async def execute(self, deliberation_id: str) -> _StatusResponse:  # type: ignore[override]
                await asyncio.sleep(0)  # Make function properly async
                self.calls.append(deliberation_id)
                if deliberation_id == "d1":
                    return _StatusResponse(status="completed")
                if deliberation_id == "d2":
                    return _StatusResponse(status="failed", error_message="boom")
                return _StatusResponse(status="running")

        usecase = _DummyStatusUseCase()
        active_deliberations: list[tuple[str, dict[str, Any]]] = [
            ("d1", {}),
            ("d2", {}),
            ("d3", {}),
        ]

        # We mainly assert that execute is called for each deliberation
        await server._process_active_deliberations(
            active_deliberations=active_deliberations,
            get_deliberation_status_usecase=usecase,  # type: ignore[arg-type]
        )

        assert usecase.calls == ["d1", "d2", "d3"]

    @pytest.mark.asyncio
    async def test_process_active_deliberations_swallows_exceptions(self) -> None:
        """Exceptions from the status use case should be swallowed per deliberation."""

        class _FailingStatusUseCase:
            async def execute(self, deliberation_id: str) -> Any:  # type: ignore[override]
                await asyncio.sleep(0)
                raise RuntimeError(f"boom {deliberation_id}")

        failing_usecase = _FailingStatusUseCase()
        active_deliberations: list[tuple[str, dict[str, Any]]] = [
            ("d1", {}),
            ("d2", {}),
        ]

        # Should not raise despite execute() failing for each deliberation
        await server._process_active_deliberations(
            active_deliberations=active_deliberations,
            get_deliberation_status_usecase=failing_usecase,  # type: ignore[arg-type]
        )


class TestPollDeliberations:
    """Unit tests for _poll_deliberations cancellation and empty-registry behavior."""

    @pytest.mark.asyncio
    async def test_poll_deliberations_loops_until_cancelled(self, mocker: Any) -> None:
        # Simulate two iterations: one normal (no active deliberations) and then cancellation
        sleep_calls: list[float] = []

        async def fake_sleep(interval: float) -> None:  # noqa: ASYNC101 - Mock function replaces asyncio.sleep, cannot await it
            sleep_calls.append(interval)
            if len(sleep_calls) >= 2:
                raise asyncio.CancelledError()
            # Cannot await asyncio.sleep here because this function IS the replacement for it

        mocker.patch("services.ray_executor.server.asyncio.sleep", side_effect=fake_sleep)
        deliberations_registry: dict[str, Any] = {}

        class _DummyStatusUseCase:
            async def execute(self, deliberation_id: str) -> Any:
                # This should never be called in this test because the registry is empty.
                await asyncio.sleep(0)
                raise AssertionError(f"execute should not be called, got {deliberation_id}")

        with pytest.raises(asyncio.CancelledError):
            await server._poll_deliberations(
                deliberations_registry=deliberations_registry,
                get_deliberation_status_usecase=_DummyStatusUseCase(),  # type: ignore[arg-type]
                poll_interval=0.01,
            )

        # We should have slept at least twice before cancellation
        assert sleep_calls == [0.01, 0.01]

    @pytest.mark.asyncio
    async def test_poll_deliberations_processes_active_and_handles_errors(self, mocker: Any) -> None:
        """When there are running deliberations, _poll_deliberations should call _process_active_deliberations and
        continue even if it fails, then react correctly to cancellation.
        """

        sleep_calls: list[float] = []

        async def fake_sleep(interval: float) -> None:
            sleep_calls.append(interval)
            if len(sleep_calls) == 1:
                return
            raise asyncio.CancelledError()

        mocker.patch("services.ray_executor.server.asyncio.sleep", side_effect=fake_sleep)

        deliberations_registry: dict[str, Any] = {
            "d1": {"status": "running"},
            "d2": {"status": "completed"},
        }

        process_mock = mocker.AsyncMock(side_effect=Exception("boom"))
        mocker.patch(
            "services.ray_executor.server._process_active_deliberations",
            new=process_mock,
        )

        class _DummyStatusUseCase:
            async def execute(self, deliberation_id: str) -> Any:  # pragma: no cover - never called because we patch processor
                await asyncio.sleep(0)
                raise AssertionError(f"execute should not be called, got {deliberation_id}")

        with pytest.raises(asyncio.CancelledError):
            await server._poll_deliberations(
                deliberations_registry=deliberations_registry,
                get_deliberation_status_usecase=_DummyStatusUseCase(),  # type: ignore[arg-type]
                poll_interval=0.01,
            )

        assert sleep_calls == [0.01, 0.01]
        process_mock.assert_awaited_once()
        kwargs = process_mock.call_args.kwargs
        active_delibs = kwargs["active_deliberations"]
        assert active_delibs == [("d1", {"status": "running"})]


class TestServeEntrypoint:
    """High-level tests for serve() without starting real infra."""

    @pytest.mark.asyncio
    async def test_serve_starts_server_and_handles_keyboard_interrupt(self, mocker: Any) -> None:
        # Fake config
        config = SimpleNamespace(
            port=50051,
            ray_address="ray://test-cluster",
            nats_url="nats://localhost:4222",
            enable_nats=True,
        )
        mocker.patch("services.ray_executor.server.load_ray_executor_config", return_value=config)

        # Avoid real Ray/NATS
        mocker.patch("services.ray_executor.server._init_ray_connection")
        mocker.patch(
            "services.ray_executor.server._init_nats_connection",
            return_value=(mocker.AsyncMock(), object()),
        )

        # Shared state and DI wiring
        start_time = 123.0
        stats_tracker = {"start_time": start_time}
        deliberations_registry: dict[str, Any] = {}
        mocker.patch(
            "services.ray_executor.server._create_shared_state",
            return_value=(start_time, stats_tracker, deliberations_registry),
        )

        dummy_get_status_uc = object()
        dummy_servicer = object()
        mocker.patch(
            "services.ray_executor.server._build_use_cases_and_servicer",
            return_value=(dummy_servicer, dummy_get_status_uc),
        )

        # Fake gRPC server object
        class _DummyServer:
            def __init__(self) -> None:
                self.started = False
                self.stopped = False
                self.listening_on: list[str] = []

            async def start(self) -> None:
                await asyncio.sleep(0)  # Make function properly async
                self.started = True

            async def wait_for_termination(self) -> None:
                # Simulate Ctrl+C to trigger shutdown path
                raise KeyboardInterrupt()

            async def stop(self, grace: float) -> None:
                await asyncio.sleep(0)  # Make function properly async
                self.stopped = True

            def add_insecure_port(self, addr: str) -> None:  # pragma: no cover - simple setter
                self.listening_on.append(addr)

        dummy_server = _DummyServer()

        def _server_factory() -> _DummyServer:
            return dummy_server

        mocker.patch("services.ray_executor.server.grpc_aio.server", side_effect=_server_factory)

        # Patch gRPC service registration to no-op
        mocker.patch(
            "services.ray_executor.server.ray_executor_pb2_grpc.add_RayExecutorServiceServicer_to_server",
        )

        # Avoid running real polling loop
        async def fake_poll_deliberations(*_: Any, **__: Any) -> None:
            await asyncio.sleep(0)

        poll_mock = mocker.patch(
            "services.ray_executor.server._poll_deliberations",
            side_effect=fake_poll_deliberations,
        )

        # Patch Ray and NATS shutdown to no-op
        mocker.patch("services.ray_executor.server.ray.shutdown")

        # Because serve() handles KeyboardInterrupt internally, it should complete
        await server.serve()

        assert dummy_server.started is True
        assert dummy_server.stopped is True
        assert dummy_server.listening_on == ["[::]:50051"]
        # Ensure we attempted to start the polling loop at least once
        assert poll_mock.call_count >= 1

    @pytest.mark.asyncio
    async def test_serve_with_nats_disabled_does_not_close_nats(self, mocker: Any) -> None:
        """serve() should work even when NATS is disabled."""
        config = SimpleNamespace(
            port=50052,
            ray_address="ray://test-cluster",
            nats_url="nats://localhost:4222",
            enable_nats=False,
        )
        mocker.patch("services.ray_executor.server.load_ray_executor_config", return_value=config)

        mocker.patch("services.ray_executor.server._init_ray_connection")
        # When NATS is disabled, helper should return (None, None)
        mocker.patch(
            "services.ray_executor.server._init_nats_connection",
            return_value=(None, None),
        )

        start_time = 123.0
        stats_tracker = {"start_time": start_time}
        deliberations_registry: dict[str, Any] = {}
        mocker.patch(
            "services.ray_executor.server._create_shared_state",
            return_value=(start_time, stats_tracker, deliberations_registry),
        )

        dummy_get_status_uc = object()
        dummy_servicer = object()
        mocker.patch(
            "services.ray_executor.server._build_use_cases_and_servicer",
            return_value=(dummy_servicer, dummy_get_status_uc),
        )

        class _DummyServer:
            def __init__(self) -> None:
                self.started = False
                self.stopped = False
                self.listening_on: list[str] = []

            async def start(self) -> None:
                await asyncio.sleep(0)  # Make function properly async
                self.started = True

            async def wait_for_termination(self) -> None:
                raise KeyboardInterrupt()

            async def stop(self, grace: float) -> None:
                await asyncio.sleep(0)  # Make function properly async
                self.stopped = True

            def add_insecure_port(self, addr: str) -> None:  # pragma: no cover - simple setter
                self.listening_on.append(addr)

        dummy_server = _DummyServer()
        mocker.patch("services.ray_executor.server.grpc_aio.server", return_value=dummy_server)
        mocker.patch(
            "services.ray_executor.server.ray_executor_pb2_grpc.add_RayExecutorServiceServicer_to_server",
        )

        async def fake_poll_deliberations(*_: Any, **__: Any) -> None:
            await asyncio.sleep(0)

        mocker.patch("services.ray_executor.server._poll_deliberations", side_effect=fake_poll_deliberations)
        mocker.patch("services.ray_executor.server.ray.shutdown")

        await server.serve()

        assert dummy_server.started is True
        assert dummy_server.stopped is True
        assert dummy_server.listening_on == ["[::]:50052"]
