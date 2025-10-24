"""
Basic Tests for NATS Messaging Adapter.

Simple tests focusing on basic functionality and port contracts.
"""

import pytest

from services.orchestrator.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)
from services.orchestrator.domain.ports import MessagingError


class TestNATSMessagingAdapterBasic:
    """Test basic NATS Messaging Adapter functionality."""

    def test_implements_messaging_port(self):
        """Test that NATSMessagingAdapter implements MessagingPort interface."""
        # Verify required port methods exist
        required_methods = ['connect', 'close', 'publish', 'publish_dict', 'pull_subscribe']
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
        
        # Test that publishing raises MessagingError when not connected
        import pytest
        with pytest.raises(MessagingError, match="Not connected to NATS"):
            # This will trigger the error through publish_dict
            import asyncio
            asyncio.run(adapter.publish_dict("test.subject", {"key": "value"}))

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
    async def test_publish_dict_not_connected(self):
        """Test publishing dict when not connected."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        
        with pytest.raises(MessagingError, match="Not connected to NATS"):
            await adapter.publish_dict("test.subject", {"key": "value"})

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
        assert hasattr(adapter, 'publish_dict')
        assert hasattr(adapter, 'pull_subscribe')
        assert hasattr(adapter, 'subscribe')
