"""Unit tests for ProjectCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.context.consumers.planning.project_created_consumer import ProjectCreatedConsumer


def _make_enveloped_msg(payload: dict[str, object]) -> Mock:
    msg = Mock()
    envelope = EventEnvelope(
        event_type="planning.project.created",
        payload=payload,
        idempotency_key="idemp-test-project-created",
        correlation_id="corr-test-project-created",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="context-tests",
    )
    msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_project_created_consumer_calls_use_case():
    """Test that consumer calls SynchronizeProjectFromPlanningUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = ProjectCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    event_data = {
        "project_id": "PROJ-123",
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "owner": "tirso",
        "created_at_ms": 1699545600000,
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    project = call_args[0][0]  # First positional argument

    assert isinstance(project, Project)
    assert project.project_id.value == "PROJ-123"
    assert project.name == "Test Project"
    assert project.description == "A test project"
    assert project.status == ProjectStatus.ACTIVE
    assert project.owner == "tirso"
    assert project.created_at_ms == 1699545600000

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_project_created_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Database error")

    consumer = ProjectCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = _make_enveloped_msg(
        {
            "project_id": "PROJ-456",
            "name": "Failed Project",
            "created_at_ms": 1699545600000,
        }
    )

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_project_created_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = ProjectCreatedConsumer(
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
async def test_project_created_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()

    consumer = ProjectCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Missing project_id (required field)
    msg = _make_enveloped_msg({"name": "Incomplete Project"})

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


def test_project_created_consumer_initialization():
    """Test ProjectCreatedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = ProjectCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

