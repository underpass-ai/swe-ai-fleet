import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.orchestrator.domain.ports import MessagingPort
from services.orchestrator.infrastructure.handlers.context_consumer import (
    OrchestratorContextConsumer,
)


@pytest.fixture
def mock_messaging_port():
    """Create a mock MessagingPort."""
    port = AsyncMock(spec=MessagingPort)
    return port


@pytest.fixture
def consumer(mock_messaging_port):
    """Create consumer instance with mocked dependencies."""
    return OrchestratorContextConsumer(messaging=mock_messaging_port)


class TestOrchestratorContextConsumer:
    @pytest.mark.asyncio
    async def test_start_creates_pull_subscriptions(self, mock_messaging_port, consumer) -> None:
        """Test that start() creates PULL subscriptions for all subjects."""
        mock_pull_sub = AsyncMock()
        mock_messaging_port.pull_subscribe.return_value = mock_pull_sub

        # Avoid spinning real infinite polling loops: replace _poll_* with async mocks
        consumer._poll_context_updated = AsyncMock()  # type: ignore[attr-defined]
        consumer._poll_milestones = AsyncMock()  # type: ignore[attr-defined]
        consumer._poll_decisions = AsyncMock()  # type: ignore[attr-defined]

        await consumer.start()

        assert mock_messaging_port.pull_subscribe.call_count == 3
        mock_messaging_port.pull_subscribe.assert_any_call(
            subject="context.updated",
            durable="orch-context-updated",
            stream="CONTEXT",
        )
        mock_messaging_port.pull_subscribe.assert_any_call(
            subject="context.milestone.reached",
            durable="orch-context-milestone",
            stream="CONTEXT",
        )
        mock_messaging_port.pull_subscribe.assert_any_call(
            subject="context.decision.added",
            durable="orch-context-decision",
            stream="CONTEXT",
        )

    @pytest.mark.asyncio
    async def test_start_raises_when_pull_subscribe_fails(
        self,
        mock_messaging_port: MessagingPort,
        consumer: OrchestratorContextConsumer,
    ) -> None:
        """start() should propagate exceptions from MessagingPort.pull_subscribe."""
        mock_messaging_port.pull_subscribe.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await consumer.start()

    @pytest.mark.asyncio
    async def test_handle_context_updated_parses_and_acks(self, consumer) -> None:
        """Test _handle_context_updated() parses event and acks message."""
        mock_message = MagicMock()
        event_data = {
            "story_id": "story-1",
            "version": 2,
            "timestamp": "2025-01-01T00:00:00Z",
        }
        mock_message.data = json.dumps(event_data).encode()
        mock_message.ack = AsyncMock()

        await consumer._handle_context_updated(mock_message)

        mock_message.ack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_context_updated_naks_on_error(self, consumer) -> None:
        """Test _handle_context_updated() sends NAK on processing error."""
        mock_message = MagicMock()
        mock_message.data = b"invalid json"
        mock_message.ack = AsyncMock()
        mock_message.nak = AsyncMock()

        await consumer._handle_context_updated(mock_message)

        mock_message.nak.assert_awaited_once()
        mock_message.ack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_milestone_reached_parses_and_acks(self, consumer) -> None:
        """Test _handle_milestone_reached() parses event and acks message."""
        mock_message = MagicMock()
        event_data = {
            "milestone_id": "milestone-1",
            "milestone_name": "Phase 1 Complete",
            "story_id": "story-1",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        mock_message.data = json.dumps(event_data).encode()
        mock_message.ack = AsyncMock()

        await consumer._handle_milestone_reached(mock_message)

        mock_message.ack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_milestone_reached_naks_on_error(self, consumer: OrchestratorContextConsumer) -> None:
        """_handle_milestone_reached() should NAK when payload is invalid."""
        mock_message = MagicMock()
        mock_message.data = b"not-json"
        mock_message.ack = AsyncMock()
        mock_message.nak = AsyncMock()

        await consumer._handle_milestone_reached(mock_message)

        mock_message.nak.assert_awaited_once()
        mock_message.ack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_decision_added_parses_and_acks(self, consumer) -> None:
        """Test _handle_decision_added() parses event and acks message."""
        mock_message = MagicMock()
        event_data = {
            "decision_id": "decision-1",
            "decision_type": "APPROVE",
            "story_id": "story-1",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        mock_message.data = json.dumps(event_data).encode()
        mock_message.ack = AsyncMock()

        await consumer._handle_decision_added(mock_message)

        mock_message.ack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_decision_added_naks_on_error(self, consumer: OrchestratorContextConsumer) -> None:
        """_handle_decision_added() should NAK when payload is invalid."""
        mock_message = MagicMock()
        mock_message.data = b"this-is-not-json"
        mock_message.ack = AsyncMock()
        mock_message.nak = AsyncMock()

        await consumer._handle_decision_added(mock_message)

        mock_message.nak.assert_awaited_once()
        mock_message.ack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_poll_context_updated_logs_error_and_sleeps_on_exception(
        self,
        consumer: OrchestratorContextConsumer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_poll_context_updated() should handle unexpected exceptions and sleep before retry."""
        # Configure a fake subscription that always raises
        fake_sub = AsyncMock()
        fake_sub.fetch.side_effect = RuntimeError("fetch failed")
        consumer._updated_sub = fake_sub  # type: ignore[attr-defined]

        # Patch asyncio.sleep in the consumer module so it raises CancelledError
        # after being awaited once, to break the infinite loop deterministically.
        from services.orchestrator.infrastructure.handlers import context_consumer as cc_module

        async def _fake_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            raise asyncio.CancelledError()

        monkeypatch.setattr(cc_module.asyncio, "sleep", _fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_context_updated()

        fake_sub.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_poll_milestones_handles_exception_and_sleeps(
        self,
        consumer: OrchestratorContextConsumer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_poll_milestones() should handle unexpected exceptions and sleep before retry."""
        fake_sub = AsyncMock()
        fake_sub.fetch.side_effect = RuntimeError("boom")
        consumer._milestone_sub = fake_sub  # type: ignore[attr-defined]

        from services.orchestrator.infrastructure.handlers import context_consumer as cc_module

        async def _fake_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            raise asyncio.CancelledError()

        monkeypatch.setattr(cc_module.asyncio, "sleep", _fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_milestones()

        fake_sub.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_poll_decisions_handles_exception_and_sleeps(
        self,
        consumer: OrchestratorContextConsumer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_poll_decisions() should handle unexpected exceptions and sleep before retry."""
        fake_sub = AsyncMock()
        fake_sub.fetch.side_effect = RuntimeError("boom")
        consumer._decision_sub = fake_sub  # type: ignore[attr-defined]

        from services.orchestrator.infrastructure.handlers import context_consumer as cc_module

        async def _fake_sleep(delay: float) -> None:  # pylint: disable=unused-argument
            raise asyncio.CancelledError()

        monkeypatch.setattr(cc_module.asyncio, "sleep", _fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_decisions()

        fake_sub.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_does_not_raise(self, consumer) -> None:
        """Test stop() does not raise exceptions."""
        await consumer.stop()
        # Should not raise
