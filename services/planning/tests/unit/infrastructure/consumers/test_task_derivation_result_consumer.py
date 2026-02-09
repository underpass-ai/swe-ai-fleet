"""Unit tests for TaskDerivationResultConsumer."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.domain.value_objects.task_derivation.task_node import TaskNode
from planning.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)


def _envelope_json(event_type: str, payload: dict[str, object]) -> str:
    envelope = EventEnvelope(
        event_type=event_type,
        payload=payload,
        idempotency_key=f"idemp-test-{event_type}",
        correlation_id=f"corr-test-{event_type}",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope))


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def mock_task_derivation_service():
    """Mock TaskDerivationResultService."""
    return AsyncMock(spec=TaskDerivationResultService)


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_task_derivation_service):
    """Create TaskDerivationResultConsumer instance."""
    return TaskDerivationResultConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        task_derivation_service=mock_task_derivation_service,
    )


@pytest.mark.asyncio
async def test_stop_cancels_polling_task_and_raises_cancelled_error(consumer):
    """Test that stop() cancels the polling task and re-raises CancelledError."""
    # Arrange: Create a fake polling task that will be cancelled
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Give the task a moment to start
    await asyncio.sleep(0.01)

    # Act & Assert: stop() should re-raise CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Task should be cancelled
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_no_polling_task(consumer):
    """Test that stop() handles case where no polling task exists."""
    consumer._polling_task = None

    # Act: Should not raise
    await consumer.stop()

    # Assert: Consumer stopped successfully
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_stop_logs_cancellation_before_raising(consumer, caplog):
    """Test that stop() logs cancellation message before re-raising CancelledError."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange: Create a fake polling task
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert: Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Logging message should be present
    assert "TaskDerivationResultConsumer polling task cancelled" in caplog.text


@pytest.mark.asyncio
async def test_start_creates_subscription_and_starts_polling(consumer, mock_jetstream):
    """Test that start() creates subscription and starts polling task."""
    # Arrange: Mock subscription
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    # Act
    await consumer.start()

    # Assert: Subscription created
    mock_jetstream.pull_subscribe.assert_awaited_once()

    # Assert: Polling task created
    assert consumer._polling_task is not None

    # Cleanup: Cancel task to avoid hanging
    consumer._polling_task.cancel()
    # Don't await cancelled task - just cancel it to prevent hanging


@pytest.mark.asyncio
async def test_start_raises_exception_on_failure(consumer, mock_jetstream):
    """Test that start() raises exception when subscription fails."""
    # Arrange: Mock subscription failure
    mock_jetstream.pull_subscribe.side_effect = Exception("NATS connection failed")

    # Act & Assert: Should raise exception
    with pytest.raises(Exception, match="NATS connection failed"):
        await consumer.start()

    # Assert: No polling task created on failure
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_poll_messages_calls_fetch(consumer):
    """Test that _poll_messages() calls fetch on subscription."""
    # Arrange: Mock subscription
    mock_subscription = AsyncMock()
    mock_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError when fetch raises it
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Fetch was called
    mock_subscription.fetch.assert_awaited()


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(consumer):
    """Test that _poll_messages() handles TimeoutError and continues."""
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

    mock_subscription = AsyncMock()
    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError after handling timeout
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Fetch was called multiple times (timeout handled, loop continued)
    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_messages_handles_generic_error(consumer):
    """Test that _poll_messages() handles generic errors with backoff."""
    # Arrange: Mock subscription that raises error, then CancelledError
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        await asyncio.sleep(0)  # Make function truly async
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Connection error")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription = AsyncMock()
    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Arrange: Mock sleep to avoid delays
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        # Act & Assert: Should raise CancelledError after handling error
        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_messages()

    # Assert: Fetch was called (error handled)
    assert call_count >= 1


@pytest.mark.asyncio
async def test_handle_message_filters_non_derivation_tasks(consumer):
    """Test that _handle_message() filters out non-derivation task types."""
    # Arrange: Create mock message with non-derivation task_type
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "other-task-123",
            "constraints": {"metadata": {"task_type": "OTHER_TASK_TYPE"}},
        },
    )

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (filtered out)
    mock_msg.ack.assert_awaited_once()

    # Assert: Service not called
    consumer._task_derivation.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_processes_derivation_task_successfully(
    consumer, mock_task_derivation_service
):
    """Test that _handle_message() processes valid derivation task successfully."""
    # Arrange: Create mock message with valid derivation payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Setup database\nDESCRIPTION: Create schema\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: database"
            },
        },
    )

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Service called with correct parameters
    mock_task_derivation_service.process.assert_awaited_once()

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_story_id(consumer):
    """Test that _handle_message() handles missing story_id."""
    # Arrange: Create mock message with missing story_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {"proposal": "TITLE: Task"},
        },
    )

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Service not called
    consumer._task_derivation.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_role(consumer):
    """Test that _handle_message() handles missing role."""
    # Arrange: Create mock message with missing role
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {"proposal": "TITLE: Task"},
        },
    )

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Service not called
    consumer._task_derivation.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_empty_llm_result(consumer):
    """Test that _handle_message() handles empty LLM result."""
    # Arrange: Create mock message with empty proposal
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {"proposal": ""},
        },
    )

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Service not called
    consumer._task_derivation.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_no_parsed_tasks(consumer):
    """Test that _handle_message() handles case where mapper returns no tasks."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {"proposal": "TITLE: Task"},
        },
    )

    # Mock mapper to return empty tuple
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Service not called
    consumer._task_derivation.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_validation_error(consumer, mock_task_derivation_service):
    """Test that _handle_message() handles ValueError from service."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Setup database\nDESCRIPTION: Create schema\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: database"
            },
        },
    )

    # Mock service to raise ValueError
    mock_task_derivation_service.process.side_effect = ValueError("Circular dependency")

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (don't retry validation errors)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_generic_error(consumer, mock_task_derivation_service):
    """Test that _handle_message() handles generic exceptions."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-001",
            "story_id": "story-001",
            "role": "DEVELOPER",
            "plan_id": "plan-001",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Setup database\nDESCRIPTION: Create schema\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: database"
            },
        },
    )

    # Mock service to raise generic exception
    mock_task_derivation_service.process.side_effect = Exception("Unexpected error")

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_json_decode_error(consumer):
    """Test that _handle_message() handles invalid JSON."""
    # Arrange: Create mock message with invalid JSON
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = "invalid json"

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (JSON decode error is caught by ValueError handler, which ACKs)
    # Note: json.JSONDecodeError is a subclass of ValueError
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_with_plan_id_in_payload(consumer, mock_task_derivation_service):
    """Test that _handle_message() extracts plan_id from payload when provided."""
    # Arrange: Create mock message with plan_id in payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-plan-002",
            "story_id": "story-002",
            "plan_id": "PLAN-FROM-PAYLOAD",  # plan_id in payload
            "role": "DEVELOPER",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Test task\nDESCRIPTION: Test description\nESTIMATED_HOURS: 4\nPRIORITY: 1\nKEYWORDS: test"
            },
        },
    )

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Service called with plan_id from payload (not from task_id)
    mock_task_derivation_service.process.assert_awaited_once()
    call_args = mock_task_derivation_service.process.call_args
    assert call_args.kwargs["plan_id"] is not None
    assert call_args.kwargs["plan_id"].value == "PLAN-FROM-PAYLOAD"

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_without_plan_id_naks(consumer, mock_task_derivation_service):
    """Test that _handle_message() passes plan_id=None when missing."""
    # Arrange: Create mock message without plan_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-PLAN-FALLBACK",
            "story_id": "story-003",
            "role": "DEVELOPER",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Test task\nDESCRIPTION: Test description\nESTIMATED_HOURS: 4\nPRIORITY: 1\nKEYWORDS: test"
            },
        },
    )

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Service called with plan_id=None and message ACKed
    mock_task_derivation_service.process.assert_awaited_once()
    call_args = mock_task_derivation_service.process.call_args
    assert call_args.kwargs["plan_id"] is None
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_without_plan_id_and_invalid_task_id_naks(consumer, mock_task_derivation_service):
    """Test that _handle_message() still processes with plan_id=None when missing."""
    # Arrange: Create mock message without plan_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        "agent.response.completed",
        {
            "task_id": "derive-",
            "story_id": "story-004",
            "role": "DEVELOPER",
            "constraints": {"metadata": {"task_type": "TASK_DERIVATION"}},
            "result": {
                "proposal": "TITLE: Test task\nDESCRIPTION: Test description\nESTIMATED_HOURS: 4\nPRIORITY: 1\nKEYWORDS: test"
            },
        },
    )

    # Mock mapper to return task nodes
    mock_task_node = Mock(spec=TaskNode)
    with patch(
        "planning.infrastructure.consumers.task_derivation_result_consumer.LLMTaskDerivationMapper.from_llm_text",
        return_value=(mock_task_node,),
    ):
        # Act
        await consumer._handle_message(mock_msg)

    # Assert: Service called with plan_id=None and message ACKed
    mock_task_derivation_service.process.assert_awaited_once()
    call_args = mock_task_derivation_service.process.call_args
    assert call_args.kwargs["plan_id"] is None
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_messages_processes_multiple_messages(consumer):
    """Test that _poll_messages() processes multiple messages in batch."""
    # Arrange: Mock subscription that returns multiple messages, then CancelledError
    call_count = 0
    messages_processed = []

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        await asyncio.sleep(0)
        call_count += 1
        if call_count == 1:
            # Return 2 messages
            msg1 = AsyncMock()
            msg1.data = Mock()
            msg1.data.decode.return_value = '{"task_id": "other-task-1"}'
            msg2 = AsyncMock()
            msg2.data = Mock()
            msg2.data.decode.return_value = '{"task_id": "other-task-2"}'
            return [msg1, msg2]
        else:
            raise asyncio.CancelledError()

    async def mock_handle_message(msg):
        nonlocal messages_processed
        messages_processed.append(msg.data.decode.return_value)
        await msg.ack()

    mock_subscription = AsyncMock()
    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription
    consumer._handle_message = mock_handle_message

    # Act & Assert: Should raise CancelledError after processing messages
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Both messages were processed
    assert len(messages_processed) == 2
