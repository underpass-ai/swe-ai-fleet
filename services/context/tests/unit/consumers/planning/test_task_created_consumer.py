"""Unit tests for TaskCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from core.context.domain.task import Task
from core.context.domain.task_status import TaskStatus
from core.context.domain.task_type import TaskType
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.context.consumers.planning.task_created_consumer import TaskCreatedConsumer


def _make_enveloped_msg(payload: dict[str, object]) -> Mock:
    msg = Mock()
    envelope = EventEnvelope(
        event_type="planning.task.created",
        payload=payload,
        idempotency_key="idemp-test-task-created",
        correlation_id="corr-test-task-created",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="context-tests",
    )
    msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_task_created_consumer_calls_use_case():
    """Test that consumer calls SynchronizeTaskFromPlanningUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "task_id": "T-123",
        "plan_id": "PLAN-456",
        "title": "Implement login endpoint",
        "type": "development",
        "status": "todo",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    task = call_args[0][0]  # First positional argument

    assert isinstance(task, Task)
    assert task.task_id.value == "T-123"
    assert task.plan_id.value == "PLAN-456"
    assert task.title == "Implement login endpoint"
    assert task.type == TaskType.DEVELOPMENT
    assert task.status == TaskStatus.TODO

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_task_created_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Database error")

    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = _make_enveloped_msg(
        {
            "task_id": "T-999",
            "plan_id": "PLAN-FAIL",
            "title": "Failed Task",
            "type": "development",
            "status": "todo",
        }
    )

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_created_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    msg.data = b"invalid json{"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_task_created_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Missing task_id (required field)
    msg = _make_enveloped_msg({"plan_id": "PLAN-123", "title": "Incomplete Task"})

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_task_created_consumer_with_minimal_data():
    """Test consumer with minimal valid task data."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "task_id": "T-MIN",
        "plan_id": "PLAN-MIN",
        "title": "Minimal Task",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_task_created_consumer_initialization():
    """Test TaskCreatedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = TaskCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

