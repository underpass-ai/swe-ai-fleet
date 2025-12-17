import sys
import types
from typing import Any

import pytest

from core.orchestrator.usecases.deliberate_async_usecase import DeliberateAsync


class DummySubmission:
    def __init__(self, deliberation_id: str, status: str, message: str) -> None:
        self.deliberation_id = deliberation_id
        self.status = status
        self.message = message


class TestDeliberateAsyncExecute:
    @pytest.mark.asyncio
    async def test_execute_generates_task_id_when_missing_and_uses_backlog_review_endpoint(self, mocker) -> None:
        ray_executor = mocker.AsyncMock()
        ray_executor.execute_backlog_review_deliberation.return_value = DummySubmission(
            deliberation_id="delib-123",
            status="submitted",
            message="ok",
        )

        usecase = DeliberateAsync(ray_executor_stub=ray_executor, model="TestModel")

        result = await usecase.execute(
            task_id=None,
            task_description="Review backlog",
            role="ARCHITECT",
            num_agents=2,
            constraints={},
            workspace_path=None,
            enable_tools=False,
        )

        # A task id should be generated and passed through
        assert result["task_id"].startswith("task-")

        # Backlog review endpoint is used when there is no plan_id
        ray_executor.execute_backlog_review_deliberation.assert_awaited_once()
        call_kwargs = ray_executor.execute_backlog_review_deliberation.call_args.kwargs
        assert call_kwargs["task_description"] == "Review backlog"
        assert call_kwargs["role"] == "ARCHITECT"
        assert len(call_kwargs["agents"]) == 2
        assert all(agent["model"] == "TestModel" for agent in call_kwargs["agents"])

        assert result["deliberation_id"] == "delib-123"
        assert result["status"] == "submitted"
        assert result["message"] == "ok"
        assert result["enable_tools"] is False
        assert result["metadata"]["tools_enabled"] is False
        assert result["metadata"]["diversity_enabled"] is True

    @pytest.mark.asyncio
    async def test_execute_uses_regular_endpoint_when_plan_id_present(self, mocker) -> None:
        ray_executor = mocker.AsyncMock()
        ray_executor.execute_deliberation.return_value = DummySubmission(
            deliberation_id="delib-456",
            status="submitted",
            message="ok",
        )

        usecase = DeliberateAsync(ray_executor_stub=ray_executor, model="TestModel")

        constraints: dict[str, Any] = {"plan_id": "PLAN-1"}

        result = await usecase.execute(
            task_id="task-1",
            task_description="Derive tasks",
            role="DEV",
            num_agents=1,
            constraints=constraints,
            workspace_path=None,
            enable_tools=False,
        )

        ray_executor.execute_deliberation.assert_awaited_once()
        call_kwargs = ray_executor.execute_deliberation.call_args.kwargs
        assert call_kwargs["task_id"] == "task-1"
        assert call_kwargs["constraints"]["plan_id"] == "PLAN-1"

        assert result["task_id"] == "task-1"
        assert result["deliberation_id"] == "delib-456"
        assert result["status"] == "submitted"
        assert result["enable_tools"] is False
        assert result["metadata"]["diversity_enabled"] is False

    @pytest.mark.asyncio
    async def test_execute_requires_workspace_when_tools_enabled(self, mocker) -> None:
        ray_executor = mocker.AsyncMock()
        usecase = DeliberateAsync(ray_executor_stub=ray_executor)

        with pytest.raises(ValueError):
            await usecase.execute(
                task_id="task-1",
                task_description="Test",
                role="DEV",
                num_agents=1,
                constraints={},
                workspace_path=None,
                enable_tools=True,
            )


class TestDeliberateAsyncStatusAndDeprecated:
    @pytest.mark.asyncio
    async def test_get_deliberation_status_happy_path(self, mocker, monkeypatch) -> None:
        # Prepare dummy gen.ray_executor_pb2 module
        ray_executor_pb2 = types.SimpleNamespace()

        class DummyRequest:
            def __init__(self, deliberation_id: str) -> None:
                self.deliberation_id = deliberation_id

        ray_executor_pb2.GetDeliberationStatusRequest = DummyRequest

        gen_module = types.SimpleNamespace(ray_executor_pb2=ray_executor_pb2)
        monkeypatch.setitem(sys.modules, "gen", gen_module)
        monkeypatch.setitem(sys.modules, "gen.ray_executor_pb2", ray_executor_pb2)

        ray_executor = mocker.AsyncMock()

        # Mock response with has_field method (protobuf-like interface)
        class DummyResponse:
            def __init__(self) -> None:
                self.status = "done"
                self.result = "OK"
                self.error_message = ""

            def has_field(self, field_name: str) -> bool:
                """Check if field exists (Python naming convention)."""
                return field_name == "result"

            def __getattr__(self, name: str):  # noqa: ANN204
                """Handle protobuf-style method names like HasField."""
                if name == "HasField":
                    return self.has_field
                raise AttributeError(f"{self.__class__.__name__} has no attribute '{name}'")

        response = DummyResponse()
        ray_executor.GetDeliberationStatus.return_value = response

        usecase = DeliberateAsync(ray_executor_stub=ray_executor)

        status = await usecase.get_deliberation_status("delib-1")

        ray_executor.GetDeliberationStatus.assert_awaited_once()
        assert status["deliberation_id"] == "delib-1"
        assert status["status"] == "done"
        assert status["result"] == "OK"
        assert status["error_message"] is None

    @pytest.mark.asyncio
    async def test_get_deliberation_status_handles_exception(self, mocker, monkeypatch) -> None:
        ray_executor_pb2 = types.SimpleNamespace()

        class DummyRequest:
            def __init__(self, deliberation_id: str) -> None:
                self.deliberation_id = deliberation_id

        ray_executor_pb2.GetDeliberationStatusRequest = DummyRequest

        gen_module = types.SimpleNamespace(ray_executor_pb2=ray_executor_pb2)
        monkeypatch.setitem(sys.modules, "gen", gen_module)
        monkeypatch.setitem(sys.modules, "gen.ray_executor_pb2", ray_executor_pb2)

        ray_executor = mocker.AsyncMock()
        ray_executor.GetDeliberationStatus.side_effect = RuntimeError("boom")

        usecase = DeliberateAsync(ray_executor_stub=ray_executor)

        status = await usecase.get_deliberation_status("delib-1")

        assert status["status"] == "error"
        assert "boom" in status["error_message"]

    def test_get_job_status_is_deprecated_but_returns_status(self) -> None:
        ray_executor = object()
        usecase = DeliberateAsync(ray_executor_stub=ray_executor)

        result = usecase.get_job_status()

        assert result["status"] == "deprecated"
        assert "Use get_deliberation_status() instead" in result["message"]
