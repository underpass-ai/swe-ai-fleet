from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, List

import pytest

from services.orchestrator import init_councils as module


@dataclass
class _StatusResponse:
    status: str


@dataclass
class _CreateCouncilResponse:
    council_id: str
    agents_created: int
    agent_ids: list[str]


@dataclass
class _Council:
    role: str
    num_agents: int
    status: str
    model: str
    agents: list[Any]


@dataclass
class _Agent:
    agent_id: str


class _DummyChannel:
    def __init__(self) -> None:
        self.closed: bool = False

    async def close(self) -> None:
        self.closed = True


class _RecordingStub:
    """Stub that records calls to GetStatus and CreateCouncil."""

    def __init__(self, channel: Any) -> None:  # pylint: disable=unused-argument
        self.channel = channel
        self.status_calls: int = 0
        self.create_requests: list[Any] = []

    async def GetStatus(self, request: Any) -> _StatusResponse:  # type: ignore[override]
        # Exercise happy-path readiness
        self.status_calls += 1
        await asyncio.sleep(0)
        return _StatusResponse(status="READY")

    async def CreateCouncil(self, request: Any) -> _CreateCouncilResponse:  # type: ignore[override]
        self.create_requests.append(request)
        await asyncio.sleep(0)
        # Mark all councils as successfully created
        return _CreateCouncilResponse(
            council_id=f"council-{request.role}",
            agents_created=request.num_agents,
            agent_ids=[f"agent-{request.role}-{i}" for i in range(request.num_agents)],
        )


class TestInitCouncilsHappyPath:
    """Tests for the happy-path behaviour of init_councils()."""

    @pytest.mark.asyncio
    async def test_init_councils_creates_councils_and_returns_true(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Configure environment
        monkeypatch.setenv("ORCHESTRATOR_ADDRESS", "orchestrator:1234")
        monkeypatch.setenv("NUM_AGENTS_PER_COUNCIL", "2")

        channel = _DummyChannel()

        def _fake_channel(address: str) -> _DummyChannel:  # pylint: disable=unused-argument
            return channel

        monkeypatch.setattr(module.grpc.aio, "insecure_channel", _fake_channel)

        stub = _RecordingStub(channel)
        monkeypatch.setattr(module.orchestrator_pb2_grpc, "OrchestratorServiceStub", lambda ch: stub)

        # Speed up retries/sleeps used in the implementation without recursion.
        original_sleep = asyncio.sleep

        async def _fast_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            await original_sleep(0)

        monkeypatch.setattr(module.asyncio, "sleep", _fast_sleep)

        success = await module.init_councils()

        assert success is True
        # One status check for readiness
        assert stub.status_calls >= 1
        # Councils are created for all configured roles
        created_roles: List[str] = [req.role for req in stub.create_requests]
        assert set(created_roles) == {"DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"}
        # Channel is closed at the end
        assert channel.closed is True


class TestInitCouncilsFailureModes:
    """Tests for failure behaviour of init_councils()."""

    @pytest.mark.asyncio
    async def test_init_councils_returns_false_when_orchestrator_never_ready(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        channel = _DummyChannel()

        def _fake_channel(address: str) -> _DummyChannel:  # pylint: disable=unused-argument
            return channel

        monkeypatch.setattr(module.grpc.aio, "insecure_channel", _fake_channel)

        class _FailingStub:
            def __init__(self, ch: Any) -> None:  # pylint: disable=unused-argument
                self.calls: int = 0

            async def GetStatus(self, request: Any) -> Any:  # type: ignore[override]
                self.calls += 1
                await asyncio.sleep(0)
                raise RuntimeError("not ready")

        failing_stub = _FailingStub(channel)
        monkeypatch.setattr(module.orchestrator_pb2_grpc, "OrchestratorServiceStub", lambda ch: failing_stub)

        original_sleep = asyncio.sleep

        async def _fast_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            await original_sleep(0)

        monkeypatch.setattr(module.asyncio, "sleep", _fast_sleep)

        success = await module.init_councils()

        assert success is False
        assert channel.closed is True

    @pytest.mark.asyncio
    async def test_init_councils_partial_failures_still_return_true_if_some_created(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("NUM_AGENTS_PER_COUNCIL", "1")

        channel = _DummyChannel()

        def _fake_channel(address: str) -> _DummyChannel:  # pylint: disable=unused-argument
            return channel

        monkeypatch.setattr(module.grpc.aio, "insecure_channel", _fake_channel)

        class _PartiallyFailingStub:
            def __init__(self, ch: Any) -> None:  # pylint: disable=unused-argument
                self.created_roles: list[str] = []

            async def GetStatus(self, request: Any) -> Any:  # type: ignore[override]
                await asyncio.sleep(0)
                return _StatusResponse(status="READY")

            async def CreateCouncil(self, request: Any) -> Any:  # type: ignore[override]
                await asyncio.sleep(0)
                # Fail for QA and DATA, create for others
                if request.role in {"QA", "DATA"}:
                    return _CreateCouncilResponse(
                        council_id="",
                        agents_created=0,
                        agent_ids=[],
                    )
                self.created_roles.append(request.role)
                return _CreateCouncilResponse(
                    council_id=f"council-{request.role}",
                    agents_created=1,
                    agent_ids=[f"agent-{request.role}-0"],
                )

        stub = _PartiallyFailingStub(channel)
        monkeypatch.setattr(module.orchestrator_pb2_grpc, "OrchestratorServiceStub", lambda ch: stub)

        original_sleep = asyncio.sleep

        async def _fast_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            await original_sleep(0)

        monkeypatch.setattr(module.asyncio, "sleep", _fast_sleep)

        success = await module.init_councils()

        assert success is True
        # At least one council was created
        assert set(stub.created_roles) == {"DEV", "ARCHITECT", "DEVOPS"}
        assert channel.closed is True


class TestVerifyCouncils:
    """Tests for verify_councils()."""

    @pytest.mark.asyncio
    async def test_verify_councils_success_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        channel = _DummyChannel()

        def _fake_channel(address: str) -> _DummyChannel:  # pylint: disable=unused-argument
            return channel

        monkeypatch.setattr(module.grpc.aio, "insecure_channel", _fake_channel)

        councils: list[_Council] = [
            _Council(
                role="DEV",
                num_agents=3,
                status="ACTIVE",
                model="m",
                agents=[_Agent(agent_id="agent-1"), _Agent(agent_id="agent-2")],
            ),
        ]

        class _Stub:
            def __init__(self, ch: Any) -> None:  # pylint: disable=unused-argument
                self.list_calls: int = 0

            async def ListCouncils(self, request: Any) -> Any:  # type: ignore[override]
                self.list_calls += 1
                await asyncio.sleep(0)
                return SimpleNamespace(councils=councils)

        stub = _Stub(channel)
        monkeypatch.setattr(module.orchestrator_pb2_grpc, "OrchestratorServiceStub", lambda ch: stub)

        result = await module.verify_councils()

        assert result is True
        assert stub.list_calls == 1
        assert channel.closed is True

    @pytest.mark.asyncio
    async def test_verify_councils_failure_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        channel = _DummyChannel()

        def _fake_channel(address: str) -> _DummyChannel:  # pylint: disable=unused-argument
            return channel

        monkeypatch.setattr(module.grpc.aio, "insecure_channel", _fake_channel)

        class _FailingStub:
            def __init__(self, ch: Any) -> None:  # pylint: disable=unused-argument
                self.calls: int = 0

            async def ListCouncils(self, request: Any) -> Any:  # type: ignore[override]
                self.calls += 1
                await asyncio.sleep(0)
                raise RuntimeError("boom")

        stub = _FailingStub(channel)
        monkeypatch.setattr(module.orchestrator_pb2_grpc, "OrchestratorServiceStub", lambda ch: stub)

        result = await module.verify_councils()

        assert result is False
        assert stub.calls == 1
        assert channel.closed is True


class TestMainEntryPoint:
    """Tests for the async main() entry point logic."""

    @pytest.mark.asyncio
    async def test_main_success_exits_with_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Patch init_councils and verify_councils to short-circuit logic
        monkeypatch.setattr(module, "init_councils", lambda: asyncio.sleep(0, result=True))
        monkeypatch.setattr(module, "verify_councils", lambda: asyncio.sleep(0, result=True))

        exit_codes: list[int] = []

        def _fake_exit(code: int) -> None:
            exit_codes.append(code)
            raise SystemExit(code)

        monkeypatch.setattr(module.sys, "exit", _fake_exit)

        with pytest.raises(SystemExit) as exc_info:
            await module.main()

        assert exc_info.value.code == 0
        assert exit_codes == [0]

    @pytest.mark.asyncio
    async def test_main_init_failure_exits_with_non_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # init_councils returns False -> early exit with code 1
        monkeypatch.setattr(module, "init_councils", lambda: asyncio.sleep(0, result=False))
        # verify_councils should never be called in this scenario
        monkeypatch.setattr(module, "verify_councils", lambda: asyncio.sleep(0, result=True))

        exit_codes: list[int] = []

        def _fake_exit(code: int) -> None:
            exit_codes.append(code)
            raise SystemExit(code)

        monkeypatch.setattr(module.sys, "exit", _fake_exit)

        with pytest.raises(SystemExit) as exc_info:
            await module.main()

        assert exc_info.value.code == 1
        assert exit_codes == [1]

    @pytest.mark.asyncio
    async def test_main_verification_failure_exits_with_non_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # init_councils succeeds but verify_councils fails -> exit code 1
        monkeypatch.setattr(module, "init_councils", lambda: asyncio.sleep(0, result=True))
        monkeypatch.setattr(module, "verify_councils", lambda: asyncio.sleep(0, result=False))

        exit_codes: list[int] = []

        def _fake_exit(code: int) -> None:
            exit_codes.append(code)
            raise SystemExit(code)

        monkeypatch.setattr(module.sys, "exit", _fake_exit)

        with pytest.raises(SystemExit) as exc_info:
            await module.main()

        assert exc_info.value.code == 1
        assert exit_codes == [1]
