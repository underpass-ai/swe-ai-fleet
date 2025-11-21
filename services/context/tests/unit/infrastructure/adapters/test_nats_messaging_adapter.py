"""Tests for NatsMessagingAdapter."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)
from services.context.infrastructure.adapters.nats_messaging_adapter import (
    NatsMessagingAdapter,
)
from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
    RehydrationStatsDTO,
)


class TestNatsMessagingAdapterInit:
    """Test NatsMessagingAdapter initialization."""

    def test_init_stores_jetstream(self) -> None:
        """Test that __init__ stores JetStream context."""
        mock_js = MagicMock()
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        assert adapter._js is mock_js


class TestNatsMessagingAdapterPublishUpdateContextResponse:
    """Test publish_update_context_response method."""

    @pytest.mark.asyncio
    async def test_publish_update_context_response_success(self) -> None:
        """Test successful publishing of update context response."""
        mock_js = AsyncMock()
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        response = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=["warning1"],
        )

        await adapter.publish_update_context_response(response)

        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.call_args
        assert call_args[0][0] == "context.update.response"
        payload = json.loads(call_args[0][1].decode())
        assert payload["story_id"] == "story-1"
        assert payload["status"] == "success"
        assert payload["version"] == 1
        assert payload["hash"] == "abc123"
        assert payload["warnings"] == ["warning1"]

    @pytest.mark.asyncio
    async def test_publish_update_context_response_propagates_errors(self) -> None:
        """Test that publish propagates errors."""
        mock_js = AsyncMock()
        mock_js.publish.side_effect = RuntimeError("Publish failed")
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        response = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(RuntimeError, match="Failed to publish update context response"):
            await adapter.publish_update_context_response(response)


class TestNatsMessagingAdapterPublishRehydrateSessionResponse:
    """Test publish_rehydrate_session_response method."""

    @pytest.mark.asyncio
    async def test_publish_rehydrate_session_response_success(self) -> None:
        """Test successful publishing of rehydrate session response."""
        mock_js = AsyncMock()
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV", "QA"],
        )

        response = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        await adapter.publish_rehydrate_session_response(response)

        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.call_args
        assert call_args[0][0] == "context.rehydrate.response"
        payload = json.loads(call_args[0][1].decode())
        assert payload["case_id"] == "case-1"
        assert payload["status"] == "success"
        assert payload["generated_at_ms"] == 1000
        assert payload["packs_count"] == 2
        assert payload["stats"]["decisions"] == 5
        assert payload["stats"]["decision_edges"] == 10
        assert payload["stats"]["impacts"] == 3
        assert payload["stats"]["events"] == 2
        assert payload["stats"]["roles"] == ["DEV", "QA"]

    @pytest.mark.asyncio
    async def test_publish_rehydrate_session_response_propagates_errors(self) -> None:
        """Test that publish propagates errors."""
        mock_js = AsyncMock()
        mock_js.publish.side_effect = RuntimeError("Publish failed")
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(RuntimeError, match="Failed to publish rehydrate session response"):
            await adapter.publish_rehydrate_session_response(response)


class TestNatsMessagingAdapterPublishContextUpdated:
    """Test publish_context_updated method."""

    @pytest.mark.asyncio
    async def test_publish_context_updated_success(self) -> None:
        """Test successful publishing of context updated event."""
        mock_js = AsyncMock()
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        await adapter.publish_context_updated(story_id="story-1", version=1)

        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.call_args
        assert call_args[0][0] == "context.events.updated"
        payload = json.loads(call_args[0][1].decode())
        assert payload["event_type"] == "context.updated"
        assert payload["story_id"] == "story-1"
        assert payload["version"] == 1
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_publish_context_updated_propagates_errors(self) -> None:
        """Test that publish propagates errors."""
        mock_js = AsyncMock()
        mock_js.publish.side_effect = RuntimeError("Publish failed")
        adapter = NatsMessagingAdapter(jetstream=mock_js)

        with pytest.raises(RuntimeError, match="Failed to publish context.updated event"):
            await adapter.publish_context_updated(story_id="story-1", version=1)

