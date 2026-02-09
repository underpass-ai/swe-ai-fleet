"""Unit tests for OrchestratorAgentResponseConsumer.

Tests the PULL subscription consumer that processes agent responses.
Following Hexagonal Architecture - tests  use mocks for MessagingPort.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.orchestrator.domain.events import TaskCompletedEvent, TaskFailedEvent
from services.orchestrator.domain.ports import MessagingPort
from services.orchestrator.infrastructure.handlers.agent_response_consumer import (
    OrchestratorAgentResponseConsumer,
)


@pytest.fixture
def mock_messaging_port():
    """Create a mock MessagingPort."""
    port = AsyncMock(spec=MessagingPort)
    return port


@pytest.fixture
def mock_pull_subscription():
    """Create a mock pull subscription."""
    subscription = AsyncMock()
    subscription.fetch = AsyncMock()
    return subscription


@pytest.fixture
def consumer(mock_messaging_port):
    """Create consumer instance with mocked dependencies."""
    return OrchestratorAgentResponseConsumer(messaging=mock_messaging_port)


def _envelope_bytes(event_type: str, payload: dict[str, object]) -> bytes:
    envelope = EventEnvelope(
        event_type=event_type,
        payload=payload,
        idempotency_key=f"idemp-test-{event_type}",
        correlation_id=f"corr-test-{event_type}",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="orchestrator-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")


@pytest.mark.asyncio
async def test_start_creates_pull_subscriptions(mock_messaging_port, consumer):
    """Test that start() creates PULL subscriptions for all subjects."""
    # Arrange
    mock_pull_sub = AsyncMock()
    mock_messaging_port.pull_subscribe.return_value = mock_pull_sub

    # Avoid spinning real infinite polling loops: replace _poll_* with async mocks
    consumer._poll_completed = AsyncMock()  # type: ignore[attr-defined]
    consumer._poll_failed = AsyncMock()  # type: ignore[attr-defined]
    consumer._poll_progress = AsyncMock()  # type: ignore[attr-defined]

    # Act
    await consumer.start()

    # Assert
    assert mock_messaging_port.pull_subscribe.call_count == 3

    # Verify completed subscription
    mock_messaging_port.pull_subscribe.assert_any_call(
        subject="agent.response.completed",
        durable="orch-agent-response-completed-v3",
        stream="AGENT_RESPONSES",
    )

    # Verify failed subscription
    mock_messaging_port.pull_subscribe.assert_any_call(
        subject="agent.response.failed",
        durable="orch-agent-response-failed-v3",
        stream="AGENT_RESPONSES",
    )

    # Verify progress subscription
    mock_messaging_port.pull_subscribe.assert_any_call(
        subject="agent.response.progress",
        durable="orch-agent-response-progress-v3",
        stream="AGENT_RESPONSES",
    )
    # We intentionally do not assert on asyncio.create_task here to avoid
    # coupling tests to the internal polling loop implementation.


# Note: We don't test _poll_* methods directly because they contain infinite loops (while True)
# The loops are simple wrappers: while True: fetch → handle → continue
# We test the actual business logic in _handle_* methods below
# The infinite loops are integration-tested when running the actual service


@pytest.mark.asyncio
async def test_handle_agent_completed_publishes_event(consumer):
    """Test _handle_agent_completed() publishes TaskCompletedEvent."""
    # Arrange
    consumer.messaging = AsyncMock(spec=MessagingPort)

    mock_message = MagicMock()
    mock_message.data = _envelope_bytes(
        "agent.response.completed",
        {
            "agent_id": "agent-1",
            "role": "DEV",
            "task_id": "task-1",
            "story_id": "story-1",
            "duration_ms": 1000,
            "checks_passed": True,
            "timestamp": "2025-11-05T18:00:00Z",
        },
    )
    mock_message.ack = AsyncMock()

    # Act
    await consumer._handle_agent_completed(mock_message)

    # Assert
    consumer.messaging.publish.assert_awaited_once()
    call_args = consumer.messaging.publish.call_args
    assert call_args[0][0] == "orchestration.task.completed"
    assert isinstance(call_args[0][1], TaskCompletedEvent)

    mock_message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_agent_failed_publishes_event(consumer):
    """Test _handle_agent_failed() publishes TaskFailedEvent."""
    # Arrange
    consumer.messaging = AsyncMock(spec=MessagingPort)

    mock_message = MagicMock()
    mock_message.data = _envelope_bytes(
        "agent.response.failed",
        {
            "agent_id": "agent-1",
            "role": "DEV",
            "task_id": "task-1",
            "story_id": "story-1",
            "error": "Test error",
            "timestamp": "2025-11-05T18:00:00Z",
        },
    )
    mock_message.ack = AsyncMock()

    # Act
    await consumer._handle_agent_failed(mock_message)

    # Assert
    consumer.messaging.publish.assert_awaited_once()
    call_args = consumer.messaging.publish.call_args
    assert call_args[0][0] == "orchestration.task.failed"
    assert isinstance(call_args[0][1], TaskFailedEvent)

    mock_message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_agent_completed_naks_on_error(consumer):
    """Test _handle_agent_completed() sends NAK on processing error."""
    # Arrange
    consumer.messaging = AsyncMock(spec=MessagingPort)

    mock_message = MagicMock()
    mock_message.data = b'invalid json'
    mock_message.ack = AsyncMock()
    mock_message.nak = AsyncMock()

    # Act
    await consumer._handle_agent_completed(mock_message)

    # Assert
    mock_message.nak.assert_awaited_once()
    mock_message.ack.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_agent_failed_drops_message_without_envelope(consumer):
    """Test _handle_agent_failed() acks invalid non-envelope payloads."""
    consumer.messaging = AsyncMock(spec=MessagingPort)

    mock_message = MagicMock()
    mock_message.data = json.dumps(
        {
            "agent_id": "agent-1",
            "role": "DEV",
            "task_id": "task-1",
            "story_id": "story-1",
            "error": "Test error",
            "timestamp": "2025-11-05T18:00:00Z",
        }
    ).encode("utf-8")
    mock_message.ack = AsyncMock()
    mock_message.nak = AsyncMock()

    await consumer._handle_agent_failed(mock_message)

    mock_message.ack.assert_awaited_once()
    mock_message.nak.assert_not_awaited()
    consumer.messaging.publish.assert_not_awaited()
