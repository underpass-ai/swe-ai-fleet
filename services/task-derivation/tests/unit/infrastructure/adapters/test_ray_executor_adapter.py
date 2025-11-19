"""Tests for RayExecutorAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.infrastructure.adapters.ray_executor_adapter import (
    RayExecutorAdapter,
)


class TestRayExecutorAdapterInit:
    """Test initialization of RayExecutorAdapter."""

    def test_init_valid_address(self) -> None:
        """Test successful initialization with valid address."""
        adapter = RayExecutorAdapter(address="ray-executor:50055")
        assert adapter._address == "ray-executor:50055"
        assert adapter._timeout == 5.0

    def test_init_with_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        adapter = RayExecutorAdapter(
            address="ray-executor:50055",
            timeout_seconds=60.0,
        )
        assert adapter._timeout == 60.0

    def test_init_rejects_empty_address(self) -> None:
        """Test that initialization rejects empty address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            RayExecutorAdapter(address="")

    def test_init_rejects_whitespace_address(self) -> None:
        """Test that initialization rejects whitespace-only address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            RayExecutorAdapter(address="   ")


class TestRayExecutorAdapterSubmitTaskDerivation:
    """Test submit_task_derivation method."""

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.ray_executor_pb2")
    async def test_submit_task_derivation_success(self, mock_pb2) -> None:
        """Test successful submission of task derivation job."""
        # Mock the proto request class
        mock_request_class = MagicMock()
        mock_pb2.SubmitTaskDerivationRequest = mock_request_class

        mock_response = MagicMock()
        mock_response.derivation_request_id = "derive-plan-123"

        mock_stub = AsyncMock()
        mock_stub.SubmitTaskDerivation = AsyncMock(return_value=mock_response)

        adapter = RayExecutorAdapter(address="ray-executor:50055")
        adapter._stub = mock_stub

        plan_id = PlanId("plan-123")
        prompt = LLMPrompt("Decompose this task into subtasks")
        role = ExecutorRole("system")

        request_id = await adapter.submit_task_derivation(plan_id, prompt, role)

        assert request_id.value == "derive-plan-123"
        mock_stub.SubmitTaskDerivation.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.ray_executor_pb2")
    async def test_submit_task_derivation_handles_error(self, mock_pb2) -> None:
        """Test error handling in submit_task_derivation."""
        # Mock the proto request class
        mock_request_class = MagicMock()
        mock_pb2.SubmitTaskDerivationRequest = mock_request_class

        mock_stub = AsyncMock()
        mock_stub.SubmitTaskDerivation = AsyncMock(
            side_effect=RuntimeError("Ray Executor unavailable")
        )

        adapter = RayExecutorAdapter(address="ray-executor:50055")
        adapter._stub = mock_stub

        plan_id = PlanId("plan-123")
        prompt = LLMPrompt("Decompose this task")
        role = ExecutorRole("system")

        with pytest.raises(RuntimeError, match="Ray Executor unavailable"):
            await adapter.submit_task_derivation(plan_id, prompt, role)

    @pytest.mark.asyncio
    @patch("task_derivation.infrastructure.adapters.ray_executor_adapter.ray_executor_pb2")
    async def test_submit_task_derivation_logs_info(self, mock_pb2, caplog) -> None:
        """Test that submit_task_derivation logs appropriately."""
        import logging

        # Mock the proto request class
        mock_request_class = MagicMock()
        mock_pb2.SubmitTaskDerivationRequest = mock_request_class

        caplog.set_level(logging.INFO)

        mock_response = MagicMock()
        mock_response.derivation_request_id = "derive-plan-456"

        mock_stub = AsyncMock()
        mock_stub.SubmitTaskDerivation = AsyncMock(return_value=mock_response)

        adapter = RayExecutorAdapter(address="ray-executor:50055")
        adapter._stub = mock_stub

        plan_id = PlanId("plan-456")
        prompt = LLMPrompt("Decompose")
        role = ExecutorRole("system")

        await adapter.submit_task_derivation(plan_id, prompt, role)

        assert "Submitting derivation job" in caplog.text
        assert "plan-456" in caplog.text


class TestRayExecutorAdapterClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_with_open_channel(self) -> None:
        """Test close closes the gRPC channel."""
        mock_channel = AsyncMock()
        adapter = RayExecutorAdapter(address="ray-executor:50055")
        adapter._channel = mock_channel

        await adapter.close()

        mock_channel.close.assert_awaited_once()
        assert adapter._channel is None

    @pytest.mark.asyncio
    async def test_close_without_channel(self) -> None:
        """Test close when channel is None."""
        adapter = RayExecutorAdapter(address="ray-executor:50055")

        # Should not raise
        await adapter.close()

        assert adapter._channel is None

