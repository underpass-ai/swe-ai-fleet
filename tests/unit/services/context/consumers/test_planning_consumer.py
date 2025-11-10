"""Unit tests for PlanningEventsConsumer (legacy)."""

import json
from unittest.mock import AsyncMock, Mock
import pytest


pytestmark = pytest.mark.unit


def test_planning_consumer_initialization():
    """Test PlanningEventsConsumer initialization."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    graph_command = Mock()

    # Act
    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    # Assert
    assert consumer.nc is nc
    assert consumer.js is js
    assert consumer.cache is cache_service
    assert consumer.graph is graph_command


@pytest.mark.asyncio
async def test_handle_story_transitioned_success():
    """Test _handle_story_transitioned with valid message."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    cache_service.scan = Mock(return_value=(0, [b"key1"]))
    cache_service.delete = Mock(return_value=1)
    graph_command = Mock()
    graph_command.upsert_entity = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    msg = Mock()
    msg.data = json.dumps({
        "story_id": "STORY-123",
        "from_phase": "DISCOVERY",
        "to_phase": "PLANNING",
        "timestamp": "2025-11-10T19:00:00Z",
    }).encode()
    msg.ack = AsyncMock()

    # Act
    await consumer._handle_story_transitioned(msg)

    # Assert
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_story_transitioned_error():
    """Test _handle_story_transitioned with invalid message."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    graph_command = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    msg = Mock()
    msg.data = b"invalid json"
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_story_transitioned(msg)

    # Assert - should NAK on error
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_plan_approved_success():
    """Test _handle_plan_approved with valid message."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    graph_command = Mock()
    graph_command.upsert_entity = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    msg = Mock()
    msg.data = json.dumps({
        "story_id": "STORY-456",
        "plan_id": "PLAN-001",
        "approved_by": "user@example.com",
        "timestamp": "2025-11-10T19:00:00Z",
    }).encode()
    msg.ack = AsyncMock()

    # Act
    await consumer._handle_plan_approved(msg)

    # Assert
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_plan_approved_no_graph():
    """Test _handle_plan_approved without graph_command."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=None,  # No graph
    )

    msg = Mock()
    msg.data = json.dumps({
        "story_id": "STORY-789",
        "plan_id": "PLAN-002",
        "approved_by": "admin@example.com",
        "timestamp": "2025-11-10T20:00:00Z",
    }).encode()
    msg.ack = AsyncMock()

    # Act
    await consumer._handle_plan_approved(msg)

    # Assert - should ACK even without graph
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_plan_approved_error():
    """Test _handle_plan_approved with invalid JSON."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    graph_command = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    msg = Mock()
    msg.data = b"invalid json"
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_plan_approved(msg)

    # Assert - should NAK on error
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop():
    """Test stop method."""
    from services.context.consumers.planning_consumer import PlanningEventsConsumer

    # Arrange
    nc = Mock()
    js = Mock()
    cache_service = Mock()
    graph_command = Mock()

    consumer = PlanningEventsConsumer(
        nc=nc,
        js=js,
        cache_service=cache_service,
        graph_command=graph_command,
    )

    # Act
    await consumer.stop()

    # Assert - should complete without error
    assert True

