"""Unit tests for EpicCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from services.context.consumers.planning.epic_created_consumer import EpicCreatedConsumer


@pytest.mark.asyncio
async def test_epic_created_consumer_creates_node():
    """Test that consumer creates Epic node in Neo4j."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = EpicCreatedConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
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
    mock_graph.save_epic.assert_called_once()
    call_args = mock_graph.save_epic.call_args
    epic = call_args[1]["epic"]

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
async def test_epic_created_consumer_handles_neo4j_error():
    """Test that consumer NAKs message on Neo4j error."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.save_epic.side_effect = Exception("Neo4j constraint violation")

    consumer = EpicCreatedConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
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

