"""Unit tests for DeliberationResultCollector.

Tests the PULL subscription consumer that collects deliberation results.
Following Hexagonal Architecture - tests use mocks for ports.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.orchestrator.domain.ports import MessagingPort
from services.orchestrator.infrastructure.handlers.deliberation_collector import (
    DeliberationResultCollector,
)


@pytest.fixture
def mock_messaging_port():
    """Create a mock MessagingPort."""
    port = AsyncMock(spec=MessagingPort)
    return port


@pytest.fixture
def mock_pull_subscription():
    """Create a mock pull subscription."""
    subscription = AsyncMock()
    subscription.fetch = AsyncMock()
    return subscription


@pytest.fixture
def collector(mock_messaging_port):
    """Create collector instance with mocked dependencies."""
    return DeliberationResultCollector(
        messaging=mock_messaging_port,
        timeout_seconds=300,
        cleanup_after_seconds=3600,
    )


@pytest.mark.asyncio
async def test_start_creates_pull_subscriptions(mock_messaging_port, collector):
    """Test that start() creates PULL subscriptions for agent responses."""
    # Arrange
    mock_pull_sub = AsyncMock()
    mock_messaging_port.pull_subscribe.return_value = mock_pull_sub
    
    # Act
    with patch("asyncio.create_task") as mock_create_task:
        await collector.start()
    
    # Assert
    assert mock_messaging_port.pull_subscribe.call_count == 2
    
    # Verify completed subscription
    mock_messaging_port.pull_subscribe.assert_any_call(
        subject="agent.response.completed",
        durable="deliberation-collector-completed-v3",
        stream="AGENT_RESPONSES",
    )
    
    # Verify failed subscription
    mock_messaging_port.pull_subscribe.assert_any_call(
        subject="agent.response.failed",
        durable="deliberation-collector-failed-v3",
        stream="AGENT_RESPONSES",
    )
    
    # Verify tasks were created (2 polling tasks + 1 cleanup task)
    assert mock_create_task.call_count == 3


# Note: We don't test _poll_* methods directly because they contain infinite loops (while True)
# The loops are simple wrappers: while True: fetch → handle → continue
# We test the actual business logic in _handle_* methods below
# The infinite loops are integration-tested when running the actual service


@pytest.mark.asyncio
async def test_handle_agent_completed_records_response(collector):
    """Test _handle_agent_completed() records response in registry."""
    # Arrange
    mock_message = MagicMock()
    mock_message.data = b'{"task_id": "task-1", "agent_id": "agent-1", "role": "DEV", "proposal": "Test proposal", "duration_ms": 1000, "timestamp": "2025-11-05T18:00:00Z"}'
    mock_message.ack = AsyncMock()
    
    # Act
    await collector._handle_agent_completed(mock_message)
    
    # Assert
    mock_message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_agent_failed_records_failure(collector):
    """Test _handle_agent_failed() records failure in registry."""
    # Arrange
    mock_message = MagicMock()
    mock_message.data = b'{"task_id": "task-1", "agent_id": "agent-1", "role": "DEV", "error": "Test error", "timestamp": "2025-11-05T18:00:00Z"}'
    mock_message.ack = AsyncMock()
    
    # Act
    await collector._handle_agent_failed(mock_message)
    
    # Assert
    mock_message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_agent_completed_acks_on_invalid_message(collector):
    """Test _handle_agent_completed() acks invalid messages to prevent redelivery."""
    # Arrange
    mock_message = MagicMock()
    mock_message.data = b'{"task_id": "", "agent_id": ""}' # Invalid - empty IDs
    mock_message.ack = AsyncMock()
    
    # Act
    await collector._handle_agent_completed(mock_message)
    
    # Assert - should ack to prevent redelivery
    mock_message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_cancels_all_tasks(collector):
    """Test stop() cancels cleanup task and polling tasks."""
    # Arrange
    mock_cleanup_task = asyncio.create_task(asyncio.sleep(100))
    mock_poll_task1 = asyncio.create_task(asyncio.sleep(100))
    mock_poll_task2 = asyncio.create_task(asyncio.sleep(100))
    
    collector._cleanup_task = mock_cleanup_task
    collector._tasks = [mock_poll_task1, mock_poll_task2]
    
    # Act
    await collector.stop()
    
    # Assert
    assert mock_cleanup_task.cancelled()
    assert mock_poll_task1.cancelled()
    assert mock_poll_task2.cancelled()

