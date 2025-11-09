"""Unit tests for ProjectCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from services.context.consumers.planning.project_created_consumer import ProjectCreatedConsumer


@pytest.mark.asyncio
async def test_project_created_consumer_creates_node():
    """Test that consumer creates Project node in Neo4j."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ProjectCreatedConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    msg = Mock()
    event_data = {
        "project_id": "PROJ-123",
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "owner": "tirso",
        "created_at_ms": 1699545600000,
    }
    msg.data = json.dumps(event_data).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_graph.save_project.assert_called_once()
    call_args = mock_graph.save_project.call_args
    project = call_args[1]["project"]

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
async def test_project_created_consumer_handles_neo4j_error():
    """Test that consumer NAKs message on Neo4j error."""
    # Arrange
    mock_js = AsyncMock()

    # Create a mock that will be called via asyncio.to_thread
    # It needs to raise synchronously
    def save_project_failing(**kwargs):
        raise Exception("Neo4j connection error")

    mock_graph = Mock()
    mock_graph.save_project = save_project_failing

    consumer = ProjectCreatedConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    msg = Mock()
    msg.data = json.dumps({
        "project_id": "PROJ-456",
        "name": "Failed Project",
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
async def test_project_created_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ProjectCreatedConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
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
    mock_graph.save_project.assert_not_called()

