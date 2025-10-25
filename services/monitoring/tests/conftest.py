"""Pytest configuration and fixtures for monitoring tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.monitoring.domain.ports.connection_port import ConnectionPort
from services.monitoring.domain.ports.stream_port import StreamPort


@pytest.fixture
def mock_connection_port():
    """Create a mock ConnectionPort."""
    mock = AsyncMock(spec=ConnectionPort)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.get_stream_context = MagicMock()
    return mock


@pytest.fixture
def mock_stream_port():
    """Create a mock StreamPort."""
    mock = AsyncMock(spec=StreamPort)
    mock.set_context = MagicMock()
    mock.create_durable_consumer = AsyncMock()
    mock.pull_subscribe = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.fetch_messages = AsyncMock()
    return mock


@pytest.fixture
def mock_jetstream_context():
    """Create a mock JetStream context."""
    mock = MagicMock()
    mock.stream_info = AsyncMock()
    mock.pull_subscribe = AsyncMock()
    mock.subscribe = AsyncMock()
    return mock
