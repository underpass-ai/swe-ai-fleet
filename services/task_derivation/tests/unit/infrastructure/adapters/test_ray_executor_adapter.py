"""Tests for RayExecutorAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.infrastructure.adapters.ray_executor_adapter import (
    RayExecutorAdapter,
)


class TestRayExecutorAdapterInit:
    """Test initialization of RayExecutorAdapter."""

    def test_init_valid_parameters(self) -> None:
        """Test successful initialization with valid parameters."""
        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        assert adapter._address == "ray-executor:50056"
        assert adapter._vllm_url == "http://vllm:8000"
        assert adapter._vllm_model == "Qwen/Qwen2.5-7B-Instruct"
        assert adapter._timeout == pytest.approx(5.0)

    def test_init_with_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
            timeout_seconds=60.0,
        )
        assert adapter._timeout == pytest.approx(60.0)

    def test_init_rejects_empty_address(self) -> None:
        """Test that initialization rejects empty address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            RayExecutorAdapter(
                address="",
                vllm_url="http://vllm:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
            )

    def test_init_rejects_whitespace_address(self) -> None:
        """Test that initialization rejects whitespace-only address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            RayExecutorAdapter(
                address="   ",
                vllm_url="http://vllm:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
            )

    def test_init_rejects_empty_vllm_url(self) -> None:
        """Test that initialization rejects empty vLLM URL."""
        with pytest.raises(ValueError, match="vllm_url cannot be empty"):
            RayExecutorAdapter(
                address="ray-executor:50056",
                vllm_url="",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
            )

    def test_init_rejects_whitespace_vllm_url(self) -> None:
        """Test that initialization rejects whitespace-only vLLM URL."""
        with pytest.raises(ValueError, match="vllm_url cannot be empty"):
            RayExecutorAdapter(
                address="ray-executor:50056",
                vllm_url="   ",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
            )

    def test_init_rejects_empty_vllm_model(self) -> None:
        """Test that initialization rejects empty vLLM model."""
        with pytest.raises(ValueError, match="vllm_model cannot be empty"):
            RayExecutorAdapter(
                address="ray-executor:50056",
                vllm_url="http://vllm:8000",
                vllm_model="",
            )

    def test_init_rejects_whitespace_vllm_model(self) -> None:
        """Test that initialization rejects whitespace-only vLLM model."""
        with pytest.raises(ValueError, match="vllm_model cannot be empty"):
            RayExecutorAdapter(
                address="ray-executor:50056",
                vllm_url="http://vllm:8000",
                vllm_model="   ",
            )


class TestRayExecutorAdapterSubmitTaskDerivation:
    """Test submit_task_derivation method."""

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_success(self, mock_mapper_class) -> None:
        """Test successful submission of task derivation job."""
        # Mock the mapper
        mock_request = MagicMock()
        mock_request.task_id = "derive-plan-123"
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock the gRPC response
        mock_response = MagicMock()
        mock_response.deliberation_id = "deliberation-456"
        mock_response.status = "accepted"

        # Mock the stub
        mock_stub = AsyncMock()
        mock_stub.ExecuteDeliberation = AsyncMock(return_value=mock_response)

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._stub = mock_stub

        plan_id = PlanId("plan-123")
        story_id = StoryId("story-123")
        prompt = LLMPrompt("Decompose this task into subtasks")
        role = ExecutorRole("SYSTEM")

        request_id = await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

        # Verify DerivationRequestId is created from deliberation_id
        assert isinstance(request_id, DerivationRequestId)
        assert request_id.value == "deliberation-456"

        # Verify mapper was called with correct parameters
        mock_mapper_class.to_execute_deliberation_request.assert_called_once_with(
            plan_id=plan_id,
            story_id=story_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        # Verify gRPC call was made
        mock_stub.ExecuteDeliberation.assert_awaited_once_with(
            mock_request, timeout=5.0
        )

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_creates_channel_lazily(
        self, mock_mapper_class, monkeypatch
    ) -> None:
        """Test that channel is created lazily on first use."""
        # Mock the mapper
        mock_request = MagicMock()
        mock_request.task_id = "derive-plan-123"
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock the gRPC response
        mock_response = MagicMock()
        mock_response.deliberation_id = "deliberation-789"
        mock_response.status = "accepted"

        # Mock the stub
        mock_stub = AsyncMock()
        mock_stub.ExecuteDeliberation = AsyncMock(return_value=mock_response)

        # Mock channel creation
        mock_channel = AsyncMock()
        mock_insecure_channel = MagicMock(return_value=mock_channel)
        import grpc.aio as aio_grpc
        monkeypatch.setattr(aio_grpc, "insecure_channel", mock_insecure_channel)

        # Mock stub creation
        from task_derivation.gen import ray_executor_pb2_grpc

        if not hasattr(ray_executor_pb2_grpc, "RayExecutorServiceStub"):
            ray_executor_pb2_grpc.RayExecutorServiceStub = MagicMock

        mock_stub_class = MagicMock(return_value=mock_stub)
        monkeypatch.setattr(
            ray_executor_pb2_grpc, "RayExecutorServiceStub", mock_stub_class
        )

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        plan_id = PlanId("plan-123")
        story_id = StoryId("story-123")
        prompt = LLMPrompt("Decompose this task")
        role = ExecutorRole("SYSTEM")

        request_id = await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

        # Verify channel was created
        mock_insecure_channel.assert_called_once_with("ray-executor:50056")
        assert adapter._channel == mock_channel

        # Verify stub was created
        mock_stub_class.assert_called_once_with(mock_channel)
        assert adapter._stub == mock_stub

        # Verify result
        assert request_id.value == "deliberation-789"

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_handles_grpc_error(
        self, mock_mapper_class
    ) -> None:
        """Test error handling for gRPC errors."""
        # Mock the mapper
        mock_request = MagicMock()
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock gRPC error
        mock_stub = AsyncMock()
        grpc_error = grpc.RpcError()
        grpc_error.code = MagicMock(return_value=grpc.StatusCode.UNAVAILABLE)
        grpc_error.details = MagicMock(return_value="Service unavailable")
        mock_stub.ExecuteDeliberation = AsyncMock(side_effect=grpc_error)

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._stub = mock_stub

        plan_id = PlanId("plan-123")
        story_id = StoryId("story-123")
        prompt = LLMPrompt("Decompose this task")
        role = ExecutorRole("SYSTEM")

        with pytest.raises(grpc.RpcError):
            await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_handles_generic_error(
        self, mock_mapper_class
    ) -> None:
        """Test error handling for generic exceptions."""
        # Mock the mapper
        mock_request = MagicMock()
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock generic error
        mock_stub = AsyncMock()
        mock_stub.ExecuteDeliberation = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._stub = mock_stub

        plan_id = PlanId("plan-123")
        story_id = StoryId("story-123")
        prompt = LLMPrompt("Decompose this task")
        role = ExecutorRole("SYSTEM")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_logs_success(
        self, mock_mapper_class, caplog
    ) -> None:
        """Test that submit_task_derivation logs appropriately."""
        import logging

        caplog.set_level(logging.INFO)

        # Mock the mapper
        mock_request = MagicMock()
        mock_request.task_id = "derive-plan-456"
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock the gRPC response
        mock_response = MagicMock()
        mock_response.deliberation_id = "deliberation-789"
        mock_response.status = "accepted"

        mock_stub = AsyncMock()
        mock_stub.ExecuteDeliberation = AsyncMock(return_value=mock_response)

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._stub = mock_stub

        plan_id = PlanId("plan-456")
        story_id = StoryId("story-456")
        prompt = LLMPrompt("Decompose")
        role = ExecutorRole("SYSTEM")

        await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

        assert "Submitting derivation job" in caplog.text
        assert "plan-456" in caplog.text
        assert "Submitting task derivation to Ray Executor" in caplog.text
        assert "derive-plan-456" in caplog.text
        assert "Ray Executor accepted" in caplog.text
        assert "deliberation-789" in caplog.text
        assert "Derivation job submitted with request ID" in caplog.text

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.RayExecutorRequestMapper")
    async def test_submit_task_derivation_reuses_channel(
        self, mock_mapper_class
    ) -> None:
        """Test that channel and stub are reused on subsequent calls."""
        # Mock the mapper
        mock_request = MagicMock()
        mock_request.task_id = "derive-plan-123"
        mock_mapper_class.to_execute_deliberation_request.return_value = mock_request

        # Mock the gRPC response
        mock_response = MagicMock()
        mock_response.deliberation_id = "deliberation-456"
        mock_response.status = "accepted"

        # Mock the stub
        mock_stub = AsyncMock()
        mock_stub.ExecuteDeliberation = AsyncMock(return_value=mock_response)

        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._stub = mock_stub
        adapter._channel = AsyncMock()  # Pre-set channel

        plan_id = PlanId("plan-123")
        story_id = StoryId("story-123")
        prompt = LLMPrompt("Decompose")
        role = ExecutorRole("SYSTEM")

        # First call
        await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

        # Second call - should reuse stub
        await adapter.submit_task_derivation(plan_id, story_id, prompt, role)

        # Verify stub was called twice
        assert mock_stub.ExecuteDeliberation.await_count == 2


class TestRayExecutorAdapterClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_with_open_channel(self) -> None:
        """Test close closes the gRPC channel."""
        mock_channel = AsyncMock()
        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )
        adapter._channel = mock_channel

        await adapter.close()

        mock_channel.close.assert_awaited_once()
        assert adapter._channel is None

    @pytest.mark.asyncio
    async def test_close_without_channel(self) -> None:
        """Test close when channel is None."""
        adapter = RayExecutorAdapter(
            address="ray-executor:50056",
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        # Should not raise
        await adapter.close()

        assert adapter._channel is None
