"""Unit tests for EpicCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from services.context.consumers.planning.epic_created_consumer import EpicCreatedConsumer


@pytest.mark.asyncio
async def test_epic_created_consumer_calls_use_case():
    """Test that consumer calls SynchronizeEpicFromPlanningUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = EpicCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    event_data = {
        "epic_id": "EPIC-456",
        "project_id": "PROJ-123",
        "title": "User Authentication",
        "description": "Implement secure auth",
        "status": "active",
        "created_at_ms": 1699545600000,
    }
    msg.data = json.dumps(event_data).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    epic = call_args[0][0]  # First positional argument

    assert isinstance(epic, Epic)
    assert epic.epic_id.value == "EPIC-456"
    assert epic.project_id.value == "PROJ-123"
    assert epic.title == "User Authentication"
    assert epic.description == "Implement secure auth"
    assert epic.status == EpicStatus.ACTIVE
    assert epic.created_at_ms == 1699545600000

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_epic_created_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Database error")

    consumer = EpicCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    msg.data = json.dumps({
        "epic_id": "EPIC-789",
        "project_id": "PROJ-NONEXISTENT",
        "title": "Failed Epic",
        "created_at_ms": 1699545600000,
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_epic_created_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = EpicCreatedConsumer(
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
async def test_epic_created_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = EpicCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    # Missing epic_id (required field)
    msg.data = json.dumps({
        "project_id": "PROJ-123",
        "title": "Incomplete Epic",
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_epic_created_consumer_with_minimal_data():
    """Test consumer with minimal valid epic data."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = EpicCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    event_data = {
        "epic_id": "EPIC-MIN",
        "project_id": "PROJ-MIN",
        "title": "Minimal Epic",
        "created_at_ms": 1699545600000,
    }
    msg.data = json.dumps(event_data).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_epic_created_consumer_initialization():
    """Test EpicCreatedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = EpicCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

