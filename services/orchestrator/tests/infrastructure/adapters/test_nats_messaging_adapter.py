from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.orchestrator.domain.events import TaskCompletedEvent
from services.orchestrator.domain.ports import MessagingError
from services.orchestrator.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)


class TestNATSMessagingAdapterConnect:
    """Test NATS connection functionality."""

    @pytest.mark.asyncio
    async def test_connect_successfully_connects_and_sets_js(self, mocker) -> None:
        # In the real NATS client, jetstream() is a regular method, not async.
        # We mirror that here so adapter.js is set to the returned context object,
        # not to a coroutine.
        mock_nc = MagicMock()
        mock_js = MagicMock()
        mock_nc.jetstream.return_value = mock_js

        mocker.patch("services.orchestrator.infrastructure.adapters.nats_messaging_adapter.nats.connect", return_value=mock_nc)

        adapter = NATSMessagingAdapter("nats://localhost:4222")

        await adapter.connect()

        assert adapter.nc is mock_nc
        assert adapter.js is mock_js

    @pytest.mark.asyncio
    async def test_connect_raises_messaging_error_on_failure(self, mocker) -> None:
        mocker.patch(
            "services.orchestrator.infrastructure.adapters.nats_messaging_adapter.nats.connect",
            side_effect=Exception("Connection refused"),
        )

        adapter = NATSMessagingAdapter("nats://localhost:4222")

        with pytest.raises(MessagingError, match="NATS connection failed"):
            await adapter.connect()


class TestNATSMessagingAdapterPublish:
    """Test publish functionality."""

    @pytest.fixture
    def connected_adapter(self, mocker) -> NATSMessagingAdapter:
        """Create adapter with mocked connection."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nc.jetstream.return_value = mock_js
        adapter.nc = mock_nc
        adapter.js = mock_js
        return adapter

    @pytest.mark.asyncio
    async def test_publish_successfully_publishes_event(self, connected_adapter) -> None:
        event = TaskCompletedEvent(
            task_id="task-1",
            story_id="story-1",
            agent_id="agent-1",
            role="DEV",
            duration_ms=1000,
            checks_passed=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        await connected_adapter.publish("orchestration.task.completed", event)

        connected_adapter.js.publish.assert_awaited_once()
        call_args = connected_adapter.js.publish.call_args
        assert call_args[0][0] == "orchestration.task.completed"
        assert isinstance(call_args[0][1], bytes)

    @pytest.mark.asyncio
    async def test_publish_raises_messaging_error_on_failure(self, connected_adapter) -> None:
        connected_adapter.js.publish.side_effect = Exception("Publish failed")

        event = TaskCompletedEvent(
            task_id="task-1",
            story_id="story-1",
            agent_id="agent-1",
            role="DEV",
            duration_ms=1000,
            checks_passed=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        with pytest.raises(MessagingError, match="Failed to publish event"):
            await connected_adapter.publish("test.subject", event)


class TestNATSMessagingAdapterPublishDict:
    """Test publish_dict functionality."""

    @pytest.fixture
    def connected_adapter(self, mocker) -> NATSMessagingAdapter:
        """Create adapter with mocked connection."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nc.jetstream.return_value = mock_js
        adapter.nc = mock_nc
        adapter.js = mock_js
        return adapter

    @pytest.mark.asyncio
    async def test_publish_dict_successfully_publishes_dict(self, connected_adapter) -> None:
        data = {"key": "value", "number": 42}

        await connected_adapter.publish_dict("test.subject", data)

        connected_adapter.js.publish.assert_awaited_once()
        call_args = connected_adapter.js.publish.call_args
        assert call_args[0][0] == "test.subject"
        assert isinstance(call_args[0][1], bytes)

    @pytest.mark.asyncio
    async def test_publish_dict_raises_messaging_error_on_failure(self, connected_adapter) -> None:
        connected_adapter.js.publish.side_effect = Exception("Publish failed")

        with pytest.raises(MessagingError, match="Failed to publish dict"):
            await connected_adapter.publish_dict("test.subject", {"key": "value"})


class TestNATSMessagingAdapterSubscribe:
    """Test subscribe functionality."""

    @pytest.fixture
    def connected_adapter(self, mocker) -> NATSMessagingAdapter:
        """Create adapter with mocked connection."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nc.jetstream.return_value = mock_js
        adapter.nc = mock_nc
        adapter.js = mock_js
        return adapter

    @pytest.mark.asyncio
    async def test_subscribe_successfully_subscribes(self, connected_adapter) -> None:
        async def handler(msg) -> None:  # Test handler stub - not executed in this test
            """Test handler for subscription."""
            pass

        await connected_adapter.subscribe("test.subject", handler)

        connected_adapter.js.subscribe.assert_awaited_once()
        call_kwargs = connected_adapter.js.subscribe.call_args.kwargs
        assert call_kwargs["subject"] == "test.subject"
        assert call_kwargs["cb"] is handler
        assert call_kwargs["manual_ack"] is True

    @pytest.mark.asyncio
    async def test_subscribe_with_queue_group(self, connected_adapter) -> None:
        async def handler(msg) -> None:  # Test handler stub - not executed in this test
            """Test handler for subscription."""
            pass

        await connected_adapter.subscribe("test.subject", handler, queue_group="queue-1")

        call_kwargs = connected_adapter.js.subscribe.call_args.kwargs
        assert call_kwargs["queue"] == "queue-1"

    @pytest.mark.asyncio
    async def test_subscribe_with_durable(self, connected_adapter) -> None:
        async def handler(msg) -> None:  # Test handler stub - not executed in this test
            """Test handler for subscription."""
            pass

        await connected_adapter.subscribe("test.subject", handler, durable="durable-1")

        call_kwargs = connected_adapter.js.subscribe.call_args.kwargs
        assert call_kwargs["durable"] == "durable-1"

    @pytest.mark.asyncio
    async def test_subscribe_raises_messaging_error_on_failure(self, connected_adapter) -> None:
        connected_adapter.js.subscribe.side_effect = Exception("Subscribe failed")

        async def handler(msg) -> None:  # Test handler stub - not executed in this test
            """Test handler for subscription."""
            pass

        with pytest.raises(MessagingError, match="Failed to subscribe"):
            await connected_adapter.subscribe("test.subject", handler)


class TestNATSMessagingAdapterPullSubscribe:
    """Test pull_subscribe functionality."""

    @pytest.fixture
    def connected_adapter(self, mocker) -> NATSMessagingAdapter:
        """Create adapter with mocked connection."""
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nats_sub = AsyncMock()
        mock_js.pull_subscribe.return_value = mock_nats_sub
        mock_nc.jetstream.return_value = mock_js
        adapter.nc = mock_nc
        adapter.js = mock_js
        return adapter

    @pytest.mark.asyncio
    async def test_pull_subscribe_successfully_creates_subscription(self, connected_adapter) -> None:
        subscription = await connected_adapter.pull_subscribe(
            subject="test.subject",
            durable="test-durable",
            stream="TEST_STREAM",
        )

        connected_adapter.js.pull_subscribe.assert_awaited_once()
        call_kwargs = connected_adapter.js.pull_subscribe.call_args.kwargs
        assert call_kwargs["subject"] == "test.subject"
        assert call_kwargs["durable"] == "test-durable"
        assert call_kwargs["stream"] == "TEST_STREAM"
        assert subscription is not None

    @pytest.mark.asyncio
    async def test_pull_subscribe_raises_messaging_error_on_failure(self, connected_adapter) -> None:
        connected_adapter.js.pull_subscribe.side_effect = Exception("Pull subscribe failed")

        with pytest.raises(MessagingError, match="Failed to pull_subscribe"):
            await connected_adapter.pull_subscribe("test.subject", "durable", "STREAM")


class TestNATSMessagingAdapterClose:
    """Test close functionality."""

    @pytest.mark.asyncio
    async def test_close_closes_connection_when_connected(self, mocker) -> None:
        adapter = NATSMessagingAdapter("nats://localhost:4222")
        mock_nc = AsyncMock()
        adapter.nc = mock_nc

        await adapter.close()

        mock_nc.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_does_not_raise_when_not_connected(self) -> None:
        adapter = NATSMessagingAdapter("nats://localhost:4222")

        await adapter.close()
        # Should not raise
