"""Unit tests for DeliberationsCompleteConsumer."""

# Install a minimal fake generated module FIRST before ANY imports.
# Some infrastructure mappers import these DTOs at module import time.
import sys
from dataclasses import dataclass
from enum import Enum
from types import ModuleType

gen_pkg = ModuleType("backlog_review_processor.gen")
agent_mod = ModuleType("backlog_review_processor.gen.agent_response_payload")


class Status(str, Enum):
    completed = "completed"
    failed = "failed"


@dataclass(frozen=True)
class Metadata:
    story_id: str | None = None
    ceremony_id: str | None = None
    task_type: str | None = None
    task_id: str | None = None
    num_agents: int | None = None


@dataclass(frozen=True)
class Constraints:
    story_id: str | None = None
    plan_id: str | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    metadata: Metadata | None = None


@dataclass(frozen=True)
class AgentResponsePayload:
    task_id: str
    status: Status
    agent_id: str | None = None
    role: str | None = None
    num_agents: int | None = None
    proposal: object | None = None
    duration_ms: int | None = None
    timestamp: str | None = None
    constraints: Constraints | None = None
    artifacts: object | None = None
    summary: object | None = None
    metrics: object | None = None
    workspace_report: object | None = None


agent_mod.AgentResponsePayload = AgentResponsePayload
agent_mod.Constraints = Constraints
agent_mod.Metadata = Metadata
agent_mod.Status = Status

sys.modules["backlog_review_processor.gen"] = gen_pkg
sys.modules["backlog_review_processor.gen.agent_response_payload"] = agent_mod

# Now safe to import
import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.infrastructure.consumers.deliberations_complete_consumer import (
    DeliberationsCompleteConsumer,
)
from core.shared.events import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    mock_js = AsyncMock()
    mock_js.pull_subscribe = AsyncMock()
    return mock_js


@pytest.fixture
def mock_extract_tasks_usecase():
    """Mock ExtractTasksFromDeliberationsUseCase."""
    mock_uc = AsyncMock()
    mock_uc.execute = AsyncMock()
    return mock_uc


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_extract_tasks_usecase):
    """Create DeliberationsCompleteConsumer instance."""
    return DeliberationsCompleteConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        extract_tasks_usecase=mock_extract_tasks_usecase,
    )


@pytest.mark.asyncio
async def test_handle_message_with_envelope(consumer, mock_extract_tasks_usecase):
    """Test handling message with EventEnvelope format."""
    # Arrange
    ceremony_id = "BRC-123"
    story_id = "ST-456"

    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload={
            "ceremony_id": ceremony_id,
            "story_id": story_id,
            "agent_deliberations": [
                {
                    "agent_id": "agent-1",
                    "role": "ARCHITECT",
                    "proposal": "test",
                    "deliberated_at": "2025-12-28T10:00:00Z",
                }
            ],
        },
        idempotency_key="key-123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="backlog-review-processor",
    )

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_extract_tasks_usecase.execute.assert_awaited_once()
    call_args = mock_extract_tasks_usecase.execute.call_args

    # Verify ceremony_id and story_id were passed correctly
    assert call_args.kwargs["ceremony_id"].value == ceremony_id
    assert call_args.kwargs["story_id"].value == story_id
    assert len(call_args.kwargs["agent_deliberations"]) == 1

    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_rejects_missing_envelope(consumer, mock_extract_tasks_usecase):
    """Messages without EventEnvelope are dropped (no legacy fallback)."""
    # Arrange
    ceremony_id = "BRC-123"
    story_id = "ST-456"

    payload = {
        "ceremony_id": ceremony_id,
        "story_id": story_id,
        "agent_deliberations": [
            {
                "agent_id": "agent-1",
                "role": "QA",
                "proposal": "test",
                "deliberated_at": "2025-12-28T10:00:00Z",
            }
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode("utf-8")
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_extract_tasks_usecase.execute.assert_not_awaited()
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_missing_ceremony_id(consumer):
    """Test handling message with missing ceremony_id."""
    # Arrange
    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload={"story_id": "ST-456", "agent_deliberations": []},
        idempotency_key="key-missing-ceremony",
        correlation_id="corr-missing-ceremony",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_missing_story_id(consumer):
    """Test handling message with missing story_id."""
    # Arrange
    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload={"ceremony_id": "BRC-123", "agent_deliberations": []},
        idempotency_key="key-missing-story",
        correlation_id="corr-missing-story",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_invalid_json(consumer):
    """Test handling message with invalid JSON."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = b"invalid json {{"
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert - ACK (don't retry validation errors)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_usecase_error(consumer, mock_extract_tasks_usecase):
    """Test handling message when usecase raises error."""
    # Arrange
    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload={"ceremony_id": "BRC-123", "story_id": "ST-456", "agent_deliberations": []},
        idempotency_key="key-usecase-error",
        correlation_id="corr-usecase-error",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")
    mock_msg.nak = AsyncMock()

    mock_extract_tasks_usecase.execute.side_effect = Exception("Usecase error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_creates_subscription(mock_nats_client, mock_jetstream, mock_extract_tasks_usecase):
    """Test that start creates a durable subscription."""
    # Arrange - Mock the subscription to avoid infinite polling
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    consumer = DeliberationsCompleteConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        extract_tasks_usecase=mock_extract_tasks_usecase,
    )

    # Act - Just call start, don't await polling
    await consumer.start()

    # Assert
    mock_jetstream.pull_subscribe.assert_awaited_once()
    call_args = mock_jetstream.pull_subscribe.call_args

    # Verify subscription parameters
    assert "deliberations.complete" in str(call_args.kwargs.get("subject", ""))
    assert call_args.kwargs.get("durable") is not None
    assert call_args.kwargs.get("stream") is not None

    # Cleanup - cancel the polling task
    if consumer._polling_task:
        consumer._polling_task.cancel()


@pytest.mark.asyncio
async def test_start_handles_exception(consumer, mock_jetstream):
    """Test that start handles exceptions gracefully."""
    # Arrange
    mock_jetstream.pull_subscribe.side_effect = Exception("Connection error")

    # Act & Assert
    with pytest.raises(Exception, match="Connection error"):
        await consumer.start()


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(consumer):
    """Test that stop cancels the polling task."""
    # Arrange
    # Create a real asyncio task that we can cancel
    async def dummy_task():
        await asyncio.sleep(100)  # Long sleep

    task = asyncio.create_task(dummy_task())
    consumer._polling_task = task

    # Act & Assert - Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Verify task was cancelled
    assert task.cancelled()


@pytest.mark.asyncio
async def test_stop_no_polling_task(consumer):
    """Test that stop handles missing polling task."""
    # Arrange
    consumer._polling_task = None

    # Act - should not raise
    await consumer.stop()
