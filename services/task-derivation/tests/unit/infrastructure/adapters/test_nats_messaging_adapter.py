"""Tests for NATSMessagingAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)


class TestNATSMessagingAdapterInit:
    """Test initialization of NATSMessagingAdapter."""

    def test_init_with_valid_client(self) -> None:
        """Test successful initialization with valid NATS client."""
        mock_client = MagicMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)
        assert adapter._nats_client is mock_client

    def test_init_rejects_none_client(self) -> None:
        """Test that initialization rejects None client."""
        with pytest.raises(ValueError, match="nats_client cannot be None"):
            NATSMessagingAdapter(nats_client=None)  # type: ignore


class TestNATSMessagingAdapterPublishTaskDerivationCompleted:
    """Test publish_task_derivation_completed method."""

    @pytest.mark.asyncio
    async def test_publish_completed_event_success(self) -> None:
        """Test successful publishing of completed event."""
        mock_client = AsyncMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationCompletedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-456"),
            role=ContextRole("developer"),
            task_count=5,
        )

        await adapter.publish_task_derivation_completed(event)

        mock_client.publish.assert_awaited_once()
        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[0][0] == "task.derivation.completed"
        
        # Verify payload contains expected fields
        payload_bytes = call_args[0][1]
        assert b"task.derivation.completed" in payload_bytes
        assert b"plan-123" in payload_bytes
        assert b"story-456" in payload_bytes

    @pytest.mark.asyncio
    async def test_publish_completed_event_handles_error(self) -> None:
        """Test error handling when publishing completed event fails."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(
            side_effect=RuntimeError("NATS connection lost")
        )

        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationCompletedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-456"),
            role=ContextRole("developer"),
            task_count=5,
        )

        with pytest.raises(RuntimeError, match="NATS connection lost"):
            await adapter.publish_task_derivation_completed(event)

    @pytest.mark.asyncio
    async def test_publish_completed_event_logs_info(self, caplog) -> None:
        """Test that publish logs success."""
        import logging

        caplog.set_level(logging.INFO)

        mock_client = AsyncMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationCompletedEvent(
            plan_id=PlanId("plan-789"),
            story_id=StoryId("story-999"),
            role=ContextRole("qa"),
            task_count=3,
        )

        await adapter.publish_task_derivation_completed(event)

        assert "Published task.derivation.completed" in caplog.text
        assert "plan-789" in caplog.text
        assert "tasks: 3" in caplog.text


class TestNATSMessagingAdapterPublishTaskDerivationFailed:
    """Test publish_task_derivation_failed method."""

    @pytest.mark.asyncio
    async def test_publish_failed_event_success(self) -> None:
        """Test successful publishing of failed event."""
        mock_client = AsyncMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationFailedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-456"),
            reason="LLM timeout after 30s",
            requires_manual_review=True,
        )

        await adapter.publish_task_derivation_failed(event)

        mock_client.publish.assert_awaited_once()
        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[0][0] == "task.derivation.failed"
        
        # Verify payload contains expected fields
        payload_bytes = call_args[0][1]
        assert b"task.derivation.failed" in payload_bytes
        assert b"plan-123" in payload_bytes
        assert b"LLM timeout" in payload_bytes

    @pytest.mark.asyncio
    async def test_publish_failed_event_handles_error(self) -> None:
        """Test error handling when publishing failed event fails."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(
            side_effect=RuntimeError("NATS stream unavailable")
        )

        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationFailedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-456"),
            reason="GPU memory exhausted",
            requires_manual_review=False,
        )

        with pytest.raises(RuntimeError, match="NATS stream unavailable"):
            await adapter.publish_task_derivation_failed(event)

    @pytest.mark.asyncio
    async def test_publish_failed_event_logs_warning(self, caplog) -> None:
        """Test that publish logs warning for failures."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_client = AsyncMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationFailedEvent(
            plan_id=PlanId("plan-error"),
            story_id=StoryId("story-error"),
            reason="Invalid prompt format",
            requires_manual_review=True,
        )

        await adapter.publish_task_derivation_failed(event)

        assert "Published task.derivation.failed" in caplog.text
        assert "plan-error" in caplog.text
        assert "Invalid prompt" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_failed_event_includes_manual_review_flag(self) -> None:
        """Test that manual_review flag is included in payload."""
        mock_client = AsyncMock()
        adapter = NATSMessagingAdapter(nats_client=mock_client)

        event = TaskDerivationFailedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-456"),
            reason="Critical error",
            requires_manual_review=True,
        )

        await adapter.publish_task_derivation_failed(event)

        call_args = mock_client.publish.call_args
        payload_bytes = call_args[0][1]
        assert b"requires_manual_review" in payload_bytes
        assert b"true" in payload_bytes

