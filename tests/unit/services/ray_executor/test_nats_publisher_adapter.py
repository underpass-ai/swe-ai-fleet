"""Unit tests for NATSPublisherAdapter."""

import json
import pytest
from unittest.mock import AsyncMock, Mock

from services.ray_executor.infrastructure.adapters.nats_publisher_adapter import NATSPublisherAdapter


# =============================================================================
# Constructor Tests
# =============================================================================

class TestNATSPublisherAdapterConstructor:
    """Test adapter constructor."""

    def test_creates_with_jetstream(self):
        """Should create adapter with JetStream context."""
        jetstream = Mock()

        adapter = NATSPublisherAdapter(jetstream=jetstream)

        assert adapter._js == jetstream

    def test_creates_without_jetstream(self):
        """Should create adapter without JetStream (None)."""
        adapter = NATSPublisherAdapter(jetstream=None)

        assert adapter._js is None


# =============================================================================
# Publish Stream Event Tests
# =============================================================================

class TestNATSPublisherPublishStreamEvent:
    """Test publish_stream_event method."""

    @pytest.mark.asyncio
    async def test_publishes_event_to_nats(self):
        """Should publish streaming event to NATS."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_stream_event(
            event_type="thinking",
            agent_id="agent-123",
            data={"thought": "Analyzing problem"},
        )

        # Verify NATS publish was called
        jetstream.publish.assert_called_once()
        call_args = jetstream.publish.call_args

        # Verify subject
        subject = call_args[0][0]
        assert subject == "vllm.streaming.agent-123"

        # Verify payload
        payload = json.loads(call_args[0][1].decode())
        assert payload["type"] == "thinking"
        assert payload["agent_id"] == "agent-123"
        assert payload["thought"] == "Analyzing problem"
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_includes_timestamp_in_event(self):
        """Should include timestamp in published event."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_stream_event(
            event_type="action",
            agent_id="agent-456",
            data={"step": "execute"},
        )

        call_args = jetstream.publish.call_args
        payload = json.loads(call_args[0][1].decode())

        assert "timestamp" in payload
        assert isinstance(payload["timestamp"], (int, float))
        assert payload["timestamp"] > 0

    @pytest.mark.asyncio
    async def test_skips_when_nats_not_connected(self, caplog):
        """Should skip publishing when NATS not connected."""
        adapter = NATSPublisherAdapter(jetstream=None)

        # Should not raise
        await adapter.publish_stream_event(
            event_type="test",
            agent_id="agent-1",
            data={},
        )

        # Should log warning
        assert "NATS not connected" in caplog.text

    @pytest.mark.asyncio
    async def test_handles_publish_error_gracefully(self, caplog):
        """Should handle NATS publish errors without raising."""
        jetstream = AsyncMock()
        jetstream.publish.side_effect = Exception("NATS connection lost")

        adapter = NATSPublisherAdapter(jetstream=jetstream)

        # Should not raise (streaming is optional)
        await adapter.publish_stream_event(
            event_type="test",
            agent_id="agent-1",
            data={},
        )

        # Should log warning
        assert "Failed to publish stream event" in caplog.text


# =============================================================================
# Publish Deliberation Result Tests
# =============================================================================

class TestNATSPublisherPublishDeliberationResult:
    """Test publish_deliberation_result method."""

    @pytest.mark.asyncio
    async def test_publishes_result_to_nats(self):
        """Should publish deliberation result to NATS."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_deliberation_result(
            deliberation_id="delib-123",
            task_id="task-456",
            status="completed",
            result={"winner": "agent-1", "score": 95.0},
            error=None,
        )

        # Verify NATS publish was called
        jetstream.publish.assert_called_once()
        call_args = jetstream.publish.call_args

        # Verify subject
        subject = call_args[0][0]
        assert subject == "orchestration.deliberation.completed"

        # Verify payload
        payload = json.loads(call_args[0][1].decode())
        assert payload["event_type"] == "deliberation.completed"
        assert payload["deliberation_id"] == "delib-123"
        assert payload["task_id"] == "task-456"
        assert payload["status"] == "completed"
        assert payload["result"]["winner"] == "agent-1"
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_includes_error_when_failed(self):
        """Should include error message for failed deliberations."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_deliberation_result(
            deliberation_id="delib-123",
            task_id="task-456",
            status="failed",
            result=None,
            error="Agent crashed",
        )

        call_args = jetstream.publish.call_args
        payload = json.loads(call_args[0][1].decode())

        assert payload["status"] == "failed"
        assert payload["error"] == "Agent crashed"
        assert "result" not in payload or payload.get("result") is None

    @pytest.mark.asyncio
    async def test_omits_result_when_none(self):
        """Should omit result field when None."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_deliberation_result(
            deliberation_id="delib-123",
            task_id="task-456",
            status="running",
            result=None,
            error=None,
        )

        call_args = jetstream.publish.call_args
        payload = json.loads(call_args[0][1].decode())

        assert "result" not in payload

    @pytest.mark.asyncio
    async def test_omits_error_when_none(self):
        """Should omit error field when None."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        await adapter.publish_deliberation_result(
            deliberation_id="delib-123",
            task_id="task-456",
            status="completed",
            result={"data": "value"},
            error=None,
        )

        call_args = jetstream.publish.call_args
        payload = json.loads(call_args[0][1].decode())

        assert "error" not in payload

    @pytest.mark.asyncio
    async def test_skips_when_nats_not_connected(self, caplog):
        """Should skip publishing when NATS not connected."""
        adapter = NATSPublisherAdapter(jetstream=None)

        # Should not raise
        await adapter.publish_deliberation_result(
            deliberation_id="delib-123",
            task_id="task-456",
            status="completed",
        )

        # Should log warning
        assert "NATS not connected" in caplog.text

    @pytest.mark.asyncio
    async def test_raises_on_publish_error(self):
        """Should raise exception on publish errors (critical operation)."""
        jetstream = AsyncMock()
        jetstream.publish.side_effect = Exception("NATS connection lost")

        adapter = NATSPublisherAdapter(jetstream=jetstream)

        # Should raise (result publishing is critical)
        with pytest.raises(Exception, match="NATS connection lost"):
            await adapter.publish_deliberation_result(
                deliberation_id="delib-123",
                task_id="task-456",
                status="completed",
                result={"winner": "agent-1"},
            )


# =============================================================================
# Integration Tests
# =============================================================================

class TestNATSPublisherIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_publishes_multiple_events_sequentially(self):
        """Should handle multiple event publishes."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        # Publish 3 stream events
        for i in range(3):
            await adapter.publish_stream_event(
                event_type=f"event-{i}",
                agent_id="agent-1",
                data={"index": i},
            )

        # Verify 3 publishes
        assert jetstream.publish.call_count == 3

    @pytest.mark.asyncio
    async def test_publishes_stream_and_result_events(self):
        """Should handle both stream and result events."""
        jetstream = AsyncMock()
        adapter = NATSPublisherAdapter(jetstream=jetstream)

        # Publish stream event
        await adapter.publish_stream_event(
            event_type="thinking",
            agent_id="agent-1",
            data={"thought": "test"},
        )

        # Publish result event
        await adapter.publish_deliberation_result(
            deliberation_id="delib-1",
            task_id="task-1",
            status="completed",
        )

        # Verify both were published
        assert jetstream.publish.call_count == 2

