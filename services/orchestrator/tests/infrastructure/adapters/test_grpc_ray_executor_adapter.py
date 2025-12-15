import grpc
import pytest

from services.orchestrator.domain.entities import DeliberationStatus, DeliberationSubmission
from services.orchestrator.infrastructure.adapters.grpc_ray_executor_adapter import (
    GRPCRayExecutorAdapter,
)


class MockExecuteDeliberationResponse:
    def __init__(self, deliberation_id: str, status: str, message: str, task_id: str = "") -> None:
        self.deliberation_id = deliberation_id
        self.status = status
        self.message = message
        self.task_id = task_id


class MockGetDeliberationStatusResponse:
    def __init__(self, status: str, error_message: str = "", has_result: bool = False) -> None:
        self.status = status
        self.error_message = error_message
        self._has_result = has_result
        self.result = "result-data" if has_result else None

    def HasField(self, field_name: str) -> bool:  # noqa: N802 - Mocking protobuf interface
        return field_name == "result" and self._has_result


class TestGRPCRayExecutorAdapter:
    @pytest.mark.asyncio
    async def test_execute_deliberation_calls_stub_and_returns_submission(self, mocker) -> None:
        mock_stub = mocker.AsyncMock()
        mock_stub.ExecuteDeliberation.return_value = MockExecuteDeliberationResponse(
            deliberation_id="delib-123",
            status="submitted",
            message="OK",
            task_id="task-1",
        )

        adapter = GRPCRayExecutorAdapter(address="localhost:50056")
        adapter.stub = mock_stub

        result = await adapter.execute_deliberation(
            task_id="task-1",
            task_description="Test task",
            role="DEV",
            agents=[{"id": "agent-1", "role": "DEV"}],
            constraints={"story_id": "story-1"},
            vllm_url="http://vllm:8000",
            vllm_model="test-model",
        )

        assert isinstance(result, DeliberationSubmission)
        assert result.deliberation_id == "delib-123"
        assert result.status == "submitted"
        assert result.task_id == "task-1"
        mock_stub.ExecuteDeliberation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_deliberation_propagates_exceptions(self, mocker) -> None:
        mock_stub = mocker.AsyncMock()
        mock_stub.ExecuteDeliberation.side_effect = grpc.RpcError("Connection failed")

        adapter = GRPCRayExecutorAdapter(address="localhost:50056")
        adapter.stub = mock_stub

        with pytest.raises(grpc.RpcError):
            await adapter.execute_deliberation(
                task_id="task-1",
                task_description="Test",
                role="DEV",
                agents=[],
                constraints={},
                vllm_url="http://vllm:8000",
                vllm_model="model",
            )

    @pytest.mark.asyncio
    async def test_get_deliberation_status_calls_stub_and_returns_status(self, mocker) -> None:
        mock_stub = mocker.AsyncMock()
        mock_stub.GetDeliberationStatus.return_value = MockGetDeliberationStatusResponse(
            status="done",
            has_result=True,
        )

        adapter = GRPCRayExecutorAdapter(address="localhost:50056")
        adapter.stub = mock_stub

        result = await adapter.get_deliberation_status("delib-123")

        assert isinstance(result, DeliberationStatus)
        assert result.deliberation_id == "delib-123"
        assert result.status == "done"
        assert result.result == "result-data"
        mock_stub.GetDeliberationStatus.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_deliberation_status_propagates_exceptions(self, mocker) -> None:
        mock_stub = mocker.AsyncMock()
        mock_stub.GetDeliberationStatus.side_effect = grpc.RpcError("Not found")

        adapter = GRPCRayExecutorAdapter(address="localhost:50056")
        adapter.stub = mock_stub

        with pytest.raises(grpc.RpcError):
            await adapter.get_deliberation_status("delib-123")

    @pytest.mark.asyncio
    async def test_close_closes_channel(self, mocker) -> None:
        mock_channel = mocker.AsyncMock()
        adapter = GRPCRayExecutorAdapter(address="localhost:50056")
        adapter.channel = mock_channel

        await adapter.close()

        mock_channel.close.assert_awaited_once()

    def test_repr_returns_string_representation(self) -> None:
        # Bypass __init__ to avoid creating a real gRPC channel in a non-async context
        adapter = GRPCRayExecutorAdapter.__new__(GRPCRayExecutorAdapter)
        adapter.address = "localhost:50056"

        repr_str = repr(adapter)

        assert "GRPCRayExecutorAdapter" in repr_str
        assert "localhost:50056" in repr_str
