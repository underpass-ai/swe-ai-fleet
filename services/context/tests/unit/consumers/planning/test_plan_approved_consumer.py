"""Unit tests for PlanApprovedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from core.context.domain.plan_approval import PlanApproval
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.context.consumers.planning.plan_approved_consumer import PlanApprovedConsumer


def _make_enveloped_msg(payload: dict[str, object]) -> Mock:
    msg = Mock()
    envelope = EventEnvelope(
        event_type="planning.plan.approved",
        payload=payload,
        idempotency_key="idemp-test-plan-approved",
        correlation_id="corr-test-plan-approved",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="context-tests",
    )
    msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_plan_approved_consumer_calls_use_case():
    """Test that consumer calls RecordPlanApprovalUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "plan_id": "PLAN-123",
        "story_id": "US-456",
        "approved_by": "po@example.com",
        "timestamp": "2023-11-09T12:00:00Z",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    approval = call_args[0][0]  # First positional argument

    assert isinstance(approval, PlanApproval)
    assert approval.plan_id.value == "PLAN-123"
    assert approval.story_id.value == "US-456"
    assert approval.approved_by == "po@example.com"
    assert approval.timestamp == "2023-11-09T12:00:00Z"

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_approved_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Database error")

    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = _make_enveloped_msg(
        {
            "plan_id": "PLAN-FAIL",
            "story_id": "US-FAIL",
            "approved_by": "system",
            "timestamp": "2023-11-09T12:00:00Z",
        }
    )

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_plan_approved_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = PlanApprovedConsumer(
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
async def test_plan_approved_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Missing plan_id (required field)
    msg = _make_enveloped_msg(
        {
            "story_id": "US-123",
            "approved_by": "po@example.com",
        }
    )

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_approved_consumer_with_minimal_data():
    """Test consumer with minimal valid approval data."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "plan_id": "PLAN-MIN",
        "story_id": "US-MIN",
        "approved_by": "po@example.com",
        "timestamp": "2023-11-09T12:00:00Z",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_approved_consumer_accepts_approved_at():
    """Test consumer accepts Planning BC format: approved_at instead of timestamp."""
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    consumer = PlanApprovedConsumer(js=mock_js, use_case=mock_use_case)

    event_data = {
        "plan_id": "PLAN-APPROVED-AT",
        "story_id": "US-APPROVED-AT",
        "approved_by": "po@example.com",
        "approved_at": "2025-01-15T14:30:00+00:00",
    }
    msg = _make_enveloped_msg(event_data)

    await consumer._handle_message(msg)

    mock_use_case.execute.assert_awaited_once()
    approval = mock_use_case.execute.call_args[0][0]
    assert isinstance(approval, PlanApproval)
    assert approval.plan_id.value == "PLAN-APPROVED-AT"
    assert approval.timestamp == "2025-01-15T14:30:00+00:00"
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_plan_approved_consumer_with_different_timestamp():
    """Test consumer with different timestamp."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "plan_id": "PLAN-OPT",
        "story_id": "US-OPT",
        "approved_by": "po@example.com",
        "timestamp": "2023-11-09T12:30:00Z",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    approval = call_args[0][0]
    assert isinstance(approval, PlanApproval)
    assert approval.timestamp == "2023-11-09T12:30:00Z"

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_plan_approved_consumer_initialization():
    """Test PlanApprovedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = PlanApprovedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

