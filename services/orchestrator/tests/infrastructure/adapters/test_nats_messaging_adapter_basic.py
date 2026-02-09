"""
Basic Tests for NATS Messaging Adapter.

Simple tests focusing on basic functionality and port contracts.
"""

import pytest
from services.orchestrator.domain.ports import MessagingError
from services.orchestrator.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)


class TestNATSMessagingAdapterBasic:
    """Test basic NATS Messaging Adapter functionality."""

    def test_implements_messaging_port(self):
        """Test that NATSMessagingAdapter implements MessagingPort interface."""
        # Verify required port methods exist
        required_methods = ['connect', 'close', 'publish', 'pull_subscribe']
        for method in required_methods:
            assert hasattr(NATSMessagingAdapter, method)

    def test_initialization_with_url(self):
        """Test initialization with NATS URL."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        assert adapter.nats_url == "nats://localhost:4222"
        assert adapter.nc is None
        assert adapter.js is None

    def test_not_connected_error_message(self):
        """Test error message when not connected."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")

        from services.orchestrator.domain.events import TaskCompletedEvent

        event = TaskCompletedEvent(
            task_id="task-1",
            story_id="story-1",
            agent_id="agent-1",
            role="DEV",
            duration_ms=100,
            checks_passed=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        with pytest.raises(MessagingError, match="Not connected to NATS"):
            import asyncio
            asyncio.run(adapter.publish("test.subject", event))

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """Test disconnecting when not connected."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        # Should not raise error
        await adapter.close()

    @pytest.mark.asyncio
    async def test_publish_not_connected(self):
        """Test publishing when not connected."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        mock_event = object()
        
        with pytest.raises(MessagingError, match="Not connected to NATS"):
            await adapter.publish("test.subject", mock_event)

    @pytest.mark.asyncio
    async def test_pull_subscribe_not_connected(self):
        """Test creating pull subscription when not connected."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        with pytest.raises(MessagingError, match="Not connected to NATS"):
            await adapter.pull_subscribe("test.subject", "test-durable", "TEST_STREAM")

    def test_adapter_has_nats_attributes(self):
        """Test adapter has NATS-specific attributes."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        # NATS-specific attributes should exist
        assert hasattr(adapter, 'nc')  # NATS client
        assert hasattr(adapter, 'js')  # JetStream context
        assert hasattr(adapter, 'nats_url')  # NATS URL

    def test_adapter_implements_port_methods(self):
        """Test adapter implements all required port methods."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        # Verify adapter implements port interface
        assert hasattr(adapter, 'connect')
        assert hasattr(adapter, 'close')
        assert hasattr(adapter, 'publish')
        assert hasattr(adapter, 'pull_subscribe')
        assert hasattr(adapter, 'subscribe')
