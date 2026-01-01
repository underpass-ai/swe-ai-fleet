"""Unit tests for TaskExtractionResultConsumer."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Install a minimal fake generated module before any imports that depend on it.
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


agent_mod.AgentResponsePayload = AgentResponsePayload
agent_mod.Constraints = Constraints
agent_mod.Metadata = Metadata
agent_mod.Status = Status

sys.modules["backlog_review_processor.gen"] = gen_pkg
sys.modules["backlog_review_processor.gen.agent_response_payload"] = agent_mod

from backlog_review_processor.domain.entities.extracted_task import ExtractedTask
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.infrastructure.consumers.task_extraction_result_consumer import (
    TaskExtractionResultConsumer,
)
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper


def _make_enveloped_bytes(payload: dict) -> bytes:
    envelope = EventEnvelope(
        event_type="agent.response.completed",
        payload=payload,
        idempotency_key="idemp-brp-test",
        correlation_id="corr-brp-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="ray-executor-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def mock_planning():
    """Mock PlanningPort."""
    return AsyncMock()


@pytest.fixture
def mock_messaging():
    """Mock MessagingPort."""
    return AsyncMock()


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_planning, mock_messaging):
    """Create TaskExtractionResultConsumer instance."""
    return TaskExtractionResultConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        planning=mock_planning,
        messaging=mock_messaging,
        max_deliveries=3,
    )


@pytest.fixture
def mock_subscription():
    """Mock NATS subscription."""
    subscription = AsyncMock()
    subscription.fetch = AsyncMock(return_value=[])
    return subscription


@pytest.mark.asyncio
async def test_start_creates_subscription(consumer, mock_jetstream, mock_subscription):
    """Test that start creates subscription and starts polling."""
    # Arrange
    mock_jetstream.pull_subscribe = AsyncMock(return_value=mock_subscription)

    # Act
    await consumer.start()

    # Assert
    mock_jetstream.pull_subscribe.assert_awaited_once()
    assert consumer._subscription == mock_subscription
    assert consumer._polling_task is not None

    # Cleanup
    consumer._polling_task.cancel()
    # Ensure CancelledError is properly raised after cleanup
    with pytest.raises(asyncio.CancelledError):
        await consumer._polling_task


@pytest.mark.asyncio
async def test_start_handles_exception(consumer, mock_jetstream):
    """Test that start raises exception on failure."""
    # Arrange
    mock_jetstream.pull_subscribe = AsyncMock(side_effect=Exception("Connection failed"))

    # Act & Assert
    with pytest.raises(Exception, match="Connection failed"):
        await consumer.start()


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(consumer, mock_subscription):
    """Test that polling handles TimeoutError gracefully."""
    # Arrange: Mock subscription that raises TimeoutError, then CancelledError
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        await asyncio.sleep(0)  # Make function truly async
        call_count += 1
        if call_count == 1:
            raise TimeoutError("No messages")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError after handling timeout
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Fetch was called multiple times (timeout handled, loop continued)
    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_messages_handles_exception(consumer, mock_subscription):
    """Test that polling handles exceptions gracefully."""
    # Arrange
    consumer._subscription = mock_subscription
    mock_subscription.fetch = AsyncMock(side_effect=Exception("Network error"))

    # Act - should not raise
    task = asyncio.create_task(consumer._poll_messages())

    # Wait a bit to let it process
    await asyncio.sleep(0.1)

    # Cancel task and verify CancelledError is raised
    task.cancel()
    # The CancelledError is properly raised and propagated by pytest.raises
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_handle_canonical_event_success(consumer, mock_planning):
    """Test successful handling of canonical event."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_id = "task-123:task-extraction"

    payload = {
        "task_id": task_id,
        "story_id": story_id.value,
        "ceremony_id": ceremony_id.value,
        "tasks": [
            {
                "title": "Task 1",
                "description": "Description 1",
                "estimated_hours": 8,
                "deliberation_indices": [0, 1],
            },
            {
                "title": "Task 2",
                "description": "Description 2",
                "estimated_hours": 4,
                "deliberation_indices": [2],
            },
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.ack = AsyncMock()
    mock_planning.create_task = AsyncMock(side_effect=["TSK-001", "TSK-002"])

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    assert task_id in consumer._processed_task_ids
    assert mock_planning.create_task.await_count == 2
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_canonical_event_missing_task_id(consumer):
    """Test handling of canonical event with missing task_id."""
    # Arrange
    payload = {
        "story_id": "ST-001",
        "ceremony_id": "BRC-12345",
        "tasks": [],
    }

    mock_msg = AsyncMock()
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_canonical_event_duplicate_task_id(consumer):
    """Test idempotency handling for duplicate task_id."""
    # Arrange
    task_id = "task-123:task-extraction"
    consumer._processed_task_ids.add(task_id)

    payload = {
        "task_id": task_id,
        "story_id": "ST-001",
        "ceremony_id": "BRC-12345",
        "tasks": [{"title": "Task 1", "description": "Desc", "estimated_hours": 8, "deliberation_indices": []}],
    }

    mock_msg = AsyncMock()
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    mock_planning = consumer._planning
    mock_planning.create_task.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_canonical_event_missing_story_or_ceremony_id(consumer):
    """Test handling of canonical event with missing story_id or ceremony_id."""
    # Arrange
    payload = {
        "task_id": "task-123",
        "story_id": "",  # Missing
        "ceremony_id": "BRC-12345",
        "tasks": [],
    }

    mock_msg = AsyncMock()
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_canonical_event_no_tasks(consumer):
    """Test handling of canonical event with no tasks."""
    # Arrange
    task_id = "task-123:task-extraction"
    payload = {
        "task_id": task_id,
        "story_id": "ST-001",
        "ceremony_id": "BRC-12345",
        "tasks": [],  # No tasks
    }

    mock_msg = AsyncMock()
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    assert task_id in consumer._processed_task_ids


@pytest.mark.asyncio
async def test_handle_canonical_event_task_creation_failure(consumer, mock_planning):
    """Test handling when task creation fails."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_id = "task-123:task-extraction"

    payload = {
        "task_id": task_id,
        "story_id": story_id.value,
        "ceremony_id": ceremony_id.value,
        "tasks": [
            {
                "title": "Task 1",
                "description": "Description 1",
                "estimated_hours": 8,
                "deliberation_indices": [0],
            },
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.ack = AsyncMock()
    mock_planning.create_task = AsyncMock(return_value=None)  # Creation failed

    # Act
    await consumer._handle_canonical_event(payload, mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()  # Still ACK even if some tasks fail
    assert task_id in consumer._processed_task_ids


@pytest.mark.asyncio
async def test_create_extracted_task_success(consumer):
    """Test successful creation of ExtractedTask."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_data = {
        "title": "Task Title",
        "description": "Task Description",
        "estimated_hours": 8,
        "deliberation_indices": [0, 1],
    }

    # Act
    extracted_task = consumer._create_extracted_task(task_data, story_id, ceremony_id, 0)

    # Assert
    assert isinstance(extracted_task, ExtractedTask)
    assert extracted_task.title == "Task Title"
    assert extracted_task.description == "Task Description"
    assert extracted_task.estimated_hours == 8
    assert extracted_task.deliberation_indices == [0, 1]
    assert extracted_task.story_id == story_id
    assert extracted_task.ceremony_id == ceremony_id


@pytest.mark.asyncio
async def test_create_extracted_task_missing_title(consumer):
    """Test that missing title returns None."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_data = {
        "description": "Task Description",
        "estimated_hours": 8,
        "deliberation_indices": [],
    }

    # Act
    extracted_task = consumer._create_extracted_task(task_data, story_id, ceremony_id, 0)

    # Assert
    assert extracted_task is None


@pytest.mark.asyncio
async def test_create_extracted_task_empty_title(consumer):
    """Test that empty title returns None."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_data = {
        "title": "",
        "description": "Task Description",
        "estimated_hours": 8,
        "deliberation_indices": [],
    }

    # Act
    extracted_task = consumer._create_extracted_task(task_data, story_id, ceremony_id, 0)

    # Assert
    assert extracted_task is None


@pytest.mark.asyncio
async def test_create_extracted_task_invalid_data(consumer):
    """Test that invalid data returns None."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_data = {
        "title": "Task Title",
        "description": "Task Description",
        "estimated_hours": -1,  # Invalid (negative)
        "deliberation_indices": [],
    }

    # Act
    extracted_task = consumer._create_extracted_task(task_data, story_id, ceremony_id, 0)

    # Assert
    assert extracted_task is None


@pytest.mark.asyncio
async def test_create_task_in_planning_success(consumer, mock_planning):
    """Test successful task creation in Planning Service."""
    # Arrange
    extracted_task = ExtractedTask(
        story_id=StoryId("ST-001"),
        ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
        title="Task Title",
        description="Task Description",
        estimated_hours=8,
        deliberation_indices=[0, 1],
    )

    mock_planning.create_task = AsyncMock(return_value="TSK-001")

    # Act
    task_id = await consumer._create_task_in_planning(extracted_task)

    # Assert
    assert task_id == "TSK-001"
    mock_planning.create_task.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_in_planning_failure(consumer, mock_planning):
    """Test handling of task creation failure."""
    # Arrange
    extracted_task = ExtractedTask(
        story_id=StoryId("ST-001"),
        ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
        title="Task Title",
        description="Task Description",
        estimated_hours=8,
        deliberation_indices=[],
    )

    mock_planning.create_task = AsyncMock(side_effect=Exception("Planning Service error"))

    # Act
    task_id = await consumer._create_task_in_planning(extracted_task)

    # Assert
    assert task_id is None


@pytest.mark.asyncio
async def test_handle_message_canonical_event(consumer, mock_planning):
    """Test handling of canonical event message."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_id = "task-123:task-extraction"

    payload = {
        "task_id": task_id,
        "story_id": story_id.value,
        "ceremony_id": ceremony_id.value,
        "tasks": [
            {
                "title": "Task 1",
                "description": "Description 1",
                "estimated_hours": 8,
                "deliberation_indices": [0],
            },
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.data = _make_enveloped_bytes(payload)
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 1
    mock_msg.ack = AsyncMock()

    mock_planning.create_task = AsyncMock(return_value="TSK-001")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    assert task_id in consumer._processed_task_ids


@pytest.mark.asyncio
async def test_handle_message_non_canonical_event(consumer):
    """Test handling of non-canonical event (missing tasks array)."""
    # Arrange
    payload = {
        "task_id": "task-123",
        "story_id": "ST-001",
        "ceremony_id": "BRC-12345",
        # Missing "tasks" array
    }

    mock_msg = AsyncMock()
    mock_msg.data = _make_enveloped_bytes(payload)
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 1
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()  # Drop invalid format


@pytest.mark.asyncio
async def test_handle_message_invalid_json(consumer):
    """Test handling of invalid JSON."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = b"invalid json"
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 1
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()  # Retry


@pytest.mark.asyncio
async def test_handle_message_invalid_json_max_deliveries(consumer):
    """Test handling of invalid JSON with max deliveries exceeded."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = b"invalid json"
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 3  # Max deliveries
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()  # Drop after max retries


@pytest.mark.asyncio
async def test_handle_message_exception_max_deliveries(consumer):
    """Test handling of exception with max deliveries exceeded."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = _make_enveloped_bytes(
        {
            "task_id": "task-123",
            "story_id": "ST-001",
            "ceremony_id": "BRC-12345",
            "tasks": [],
        }
    )
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 3  # Max deliveries

    # Mock _handle_canonical_event to raise exception
    async def raise_exception(*args, **kwargs):
        raise RuntimeError("Processing error")

    consumer._handle_canonical_event = raise_exception
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()  # Drop after max retries


@pytest.mark.asyncio
async def test_handle_message_exception_retry(consumer):
    """Test handling of exception with retry."""
    # Arrange
    mock_msg = AsyncMock()
    # Use canonical format (with tasks array) so it reaches _handle_canonical_event
    mock_msg.data = _make_enveloped_bytes(
        {
            "task_id": "task-123",
            "story_id": "ST-001",
            "ceremony_id": "BRC-12345",
            "tasks": [],
        }
    )
    mock_msg.metadata = Mock()
    mock_msg.metadata.num_delivered = 1  # Below max

    # Mock _handle_canonical_event to raise exception
    async def raise_exception(*args, **kwargs):
        raise RuntimeError("Processing error")

    consumer._handle_canonical_event = raise_exception
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()  # Retry


@pytest.mark.asyncio
async def test_handle_message_no_metadata(consumer, mock_planning):
    """Test handling of message without metadata."""
    # Arrange
    story_id = StoryId("ST-001")
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    task_id = "task-123:task-extraction"

    payload = {
        "task_id": task_id,
        "story_id": story_id.value,
        "ceremony_id": ceremony_id.value,
        "tasks": [
            {
                "title": "Task 1",
                "description": "Description 1",
                "estimated_hours": 8,
                "deliberation_indices": [0],
            },
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.data = _make_enveloped_bytes(payload)
    mock_msg.metadata = None  # No metadata
    mock_msg.ack = AsyncMock()

    mock_planning.create_task = AsyncMock(return_value="TSK-001")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(consumer):
    """Test that stop cancels polling task."""
    # Arrange
    mock_task = AsyncMock()
    consumer._polling_task = mock_task
    mock_task.cancel = Mock()
    mock_task.__await__ = Mock(return_value=iter([]))

    # Act
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert
    mock_task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_stop_no_polling_task(consumer):
    """Test that stop handles missing polling task."""
    # Arrange
    consumer._polling_task = None

    # Act - should not raise
    await consumer.stop()


@pytest.mark.asyncio
async def test_publish_tasks_complete_event(consumer, mock_messaging):
    """Test publishing tasks complete event."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-12345")
    story_id = StoryId("ST-001")
    tasks_created = 3

    # Act
    await consumer._publish_tasks_complete_event(ceremony_id, story_id, tasks_created)

    # Assert - Now uses publish_event_with_envelope
    mock_messaging.publish_event_with_envelope.assert_awaited_once()
    call_args = mock_messaging.publish_event_with_envelope.call_args
    # call_args is a tuple: (args, kwargs) or call object
    # Access positional args with [0] and kwargs with [1] or use .args and .kwargs
    subject = call_args.kwargs["subject"] if "subject" in call_args.kwargs else call_args[0][0]
    envelope = call_args.kwargs["envelope"] if "envelope" in call_args.kwargs else call_args[0][1]

    assert "tasks.complete" in subject
    # Verify envelope has required fields
    assert hasattr(envelope, "idempotency_key")
    assert hasattr(envelope, "correlation_id")
    assert hasattr(envelope, "payload")
    # Verify payload content
    payload = envelope.payload
    assert payload["ceremony_id"] == ceremony_id.value
    assert payload["story_id"] == story_id.value
    assert payload["tasks_created"] == tasks_created
