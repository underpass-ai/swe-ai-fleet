"""Tests for ContextNATSHandler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper

from services.context.nats_handler import ContextNATSHandler


def _enveloped_json(
    event_type: str,
    payload: dict[str, object],
    entity_id: str,
) -> str:
    """Build an EventEnvelope JSON string for NATS handler tests."""
    envelope = create_event_envelope(
        event_type=event_type,
        payload=payload,
        producer="context-tests",
        entity_id=entity_id,
        operation="test",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope))


class TestContextNATSHandlerInit:
    """Test ContextNATSHandler initialization."""

    def test_init_sets_attributes(self) -> None:
        """Test that __init__ sets nats_url and context_service."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        assert handler.nats_url == "nats://localhost:4222"
        assert handler.context_service is mock_service

    def test_init_sets_connected_false(self) -> None:
        """Test that __init__ sets _connected to False via base class."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        assert handler._connected is False
        assert handler._is_connected() is False


class TestContextNATSHandlerProperties:
    """Test ContextNATSHandler properties."""

    def test_nc_raises_when_not_connected(self) -> None:
        """Test nc property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.nc

    def test_js_raises_when_not_connected(self) -> None:
        """Test js property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.js

    def test_messaging_raises_when_not_connected(self) -> None:
        """Test messaging property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.messaging

    def test_publish_context_updated_uc_raises_when_not_connected(self) -> None:
        """Test publish_context_updated_uc property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.publish_context_updated_uc

    def test_publish_update_response_uc_raises_when_not_connected(self) -> None:
        """Test publish_update_response_uc property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.publish_update_response_uc

    def test_publish_rehydrate_response_uc_raises_when_not_connected(self) -> None:
        """Test publish_rehydrate_response_uc property raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="NATS not connected"):
            _ = handler.publish_rehydrate_response_uc

    def test_properties_return_values_when_connected(self) -> None:
        """Test properties return values when connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        # Set up connected state
        mock_nc = MagicMock()
        mock_js = MagicMock()
        mock_messaging = MagicMock()
        mock_uc1 = MagicMock()
        mock_uc2 = MagicMock()
        mock_uc3 = MagicMock()

        handler._nc = mock_nc
        handler._js = mock_js
        handler._messaging = mock_messaging
        handler._publish_context_updated_uc = mock_uc1
        handler._publish_update_response_uc = mock_uc2
        handler._publish_rehydrate_response_uc = mock_uc3
        handler._connected = True

        assert handler.nc is mock_nc
        assert handler.js is mock_js
        assert handler.messaging is mock_messaging
        assert handler.publish_context_updated_uc is mock_uc1
        assert handler.publish_update_response_uc is mock_uc2
        assert handler.publish_rehydrate_response_uc is mock_uc3


class TestContextNATSHandlerConnect:
    """Test connect method."""

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.nats.connect")
    async def test_connect_success(self, mock_nats_connect: MagicMock) -> None:
        """Test successful connection."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_nc = AsyncMock()
        mock_js = MagicMock()
        # jetstream() is a regular method, not async
        mock_nc.jetstream = MagicMock(return_value=mock_js)
        mock_nats_connect.return_value = mock_nc

        mock_js.add_stream = AsyncMock()

        await handler.connect()

        assert handler._connected is True
        assert handler._nc is mock_nc
        assert handler._js is mock_js
        mock_nats_connect.assert_awaited_once_with("nats://localhost:4222")
        mock_nc.jetstream.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.nats.connect")
    async def test_connect_initializes_components(self, mock_nats_connect: MagicMock) -> None:
        """Test connect initializes messaging adapter and use cases."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_nc = AsyncMock()
        mock_js = MagicMock()
        mock_nc.jetstream.return_value = mock_js
        mock_nats_connect.return_value = mock_nc
        mock_js.add_stream = AsyncMock()

        await handler.connect()

        assert handler._messaging is not None
        assert handler._publish_context_updated_uc is not None
        assert handler._publish_update_response_uc is not None
        assert handler._publish_rehydrate_response_uc is not None

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.nats.connect")
    async def test_connect_handles_stream_creation_error(self, mock_nats_connect: MagicMock) -> None:
        """Test connect handles stream creation errors gracefully."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_nc = AsyncMock()
        mock_js = MagicMock()
        mock_nc.jetstream.return_value = mock_js
        mock_nats_connect.return_value = mock_nc
        mock_js.add_stream = AsyncMock(side_effect=Exception("Stream exists"))

        # Should not raise, just log
        await handler.connect()

        assert handler._connected is True

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.nats.connect")
    async def test_connect_propagates_connection_errors(self, mock_nats_connect: MagicMock) -> None:
        """Test connect propagates connection errors."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_nats_connect.side_effect = RuntimeError("Connection failed")

        with pytest.raises(RuntimeError, match="Connection failed"):
            await handler.connect()

        assert handler._connected is False


class TestContextNATSHandlerSubscribe:
    """Test subscribe method."""

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self) -> None:
        """Test subscribe raises when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        with pytest.raises(RuntimeError, match="Not connected to NATS"):
            await handler.subscribe()

    @pytest.mark.asyncio
    async def test_subscribe_calls_js_subscribe(self) -> None:
        """Test subscribe calls js.subscribe for both subjects."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_js = AsyncMock()
        handler._js = mock_js
        handler._connected = True

        await handler.subscribe()

        assert mock_js.subscribe.call_count == 2
        calls = [call[0][0] for call in mock_js.subscribe.call_args_list]
        assert "context.update.request" in calls
        assert "context.rehydrate.request" in calls


class TestContextNATSHandlerPublishContextUpdated:
    """Test publish_context_updated method."""

    @pytest.mark.asyncio
    async def test_publish_context_updated_warns_when_not_connected(self) -> None:
        """Test publish_context_updated warns when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        # Should not raise, just return
        await handler.publish_context_updated("story-1", 1)

    @pytest.mark.asyncio
    async def test_publish_context_updated_calls_use_case_when_connected(self) -> None:
        """Test publish_context_updated calls use case when connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_uc = AsyncMock()
        handler._publish_context_updated_uc = mock_uc
        handler._connected = True

        await handler.publish_context_updated("story-1", 1)

        mock_uc.execute.assert_awaited_once_with("story-1", 1)


class TestContextNATSHandlerClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_calls_nc_close_when_connected(self) -> None:
        """Test close calls _nc.close when connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_nc = AsyncMock()
        handler._nc = mock_nc
        handler._connected = True

        await handler.close()

        mock_nc.close.assert_awaited_once()
        assert handler._connected is False

    @pytest.mark.asyncio
    async def test_close_does_nothing_when_not_connected(self) -> None:
        """Test close does nothing when not connected."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        handler._connected = False

        await handler.close()

        assert handler._connected is False


class TestContextNATSHandlerHandleUpdateRequest:
    """Test _handle_update_request method."""

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.NatsProtobufMapper")
    @patch("services.context.nats_handler.InternalServicerContext")
    @patch("services.context.nats_handler.ServicerContextErrorHandler")
    @patch("services.context.nats_handler.ProtobufResponseMapper")
    async def test_handle_update_request_success(
        self,
        mock_response_mapper: MagicMock,
        mock_error_handler: MagicMock,
        mock_context: MagicMock,
        mock_protobuf_mapper: MagicMock,
    ) -> None:
        """Test successful update request handling."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        # Setup mocks
        mock_msg = MagicMock()
        update_payload = {"story_id": "story-1", "task_id": "task-1"}
        mock_msg.data.decode.return_value = _enveloped_json(
            event_type="context.update.request",
            payload=update_payload,
            entity_id="story-1",
        )
        mock_msg.ack = AsyncMock()

        mock_request = MagicMock()
        mock_protobuf_mapper.to_update_context_request.return_value = mock_request

        mock_grpc_context = MagicMock()
        mock_context.return_value = mock_grpc_context

        mock_response = MagicMock()
        mock_response.version = 1
        mock_service.UpdateContext = AsyncMock(return_value=mock_response)

        mock_response_dto = MagicMock()
        mock_response_mapper.to_update_context_response_dto.return_value = mock_response_dto

        mock_uc = AsyncMock()
        handler._publish_update_response_uc = mock_uc
        handler._connected = True

        await handler._handle_update_request(mock_msg)

        mock_protobuf_mapper.to_update_context_request.assert_called_once()
        mock_service.UpdateContext.assert_awaited_once()
        mock_error_handler.check_and_raise.assert_called_once()
        mock_response_mapper.to_update_context_response_dto.assert_called_once()
        mock_uc.execute.assert_awaited_once_with(mock_response_dto)
        mock_msg.ack.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.NatsProtobufMapper")
    async def test_handle_update_request_acks_invalid_envelope(
        self,
        mock_protobuf_mapper: MagicMock,
    ) -> None:
        """Test invalid non-enveloped payload is dropped (ACK, no processing)."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_msg = MagicMock()
        mock_msg.data.decode.return_value = json.dumps({"story_id": "story-1", "task_id": "task-1"})
        mock_msg.ack = AsyncMock()
        mock_msg.nak = AsyncMock()

        await handler._handle_update_request(mock_msg)

        mock_protobuf_mapper.to_update_context_request.assert_not_called()
        mock_msg.ack.assert_awaited_once()
        mock_msg.nak.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_update_request_naks_on_error(self) -> None:
        """Test update request sends NAK on error."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_msg = MagicMock()
        mock_msg.data.decode.side_effect = ValueError("Invalid JSON")
        mock_msg.nak = AsyncMock()

        await handler._handle_update_request(mock_msg)

        mock_msg.nak.assert_awaited_once()


class TestContextNATSHandlerHandleRehydrateRequest:
    """Test _handle_rehydrate_request method."""

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.NatsProtobufMapper")
    @patch("services.context.nats_handler.InternalServicerContext")
    @patch("services.context.nats_handler.ServicerContextErrorHandler")
    @patch("services.context.nats_handler.ProtobufResponseMapper")
    async def test_handle_rehydrate_request_success(
        self,
        mock_response_mapper: MagicMock,
        mock_error_handler: MagicMock,
        mock_context: MagicMock,
        mock_protobuf_mapper: MagicMock,
    ) -> None:
        """Test successful rehydrate request handling."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        # Setup mocks
        mock_msg = MagicMock()
        rehydrate_payload = {"case_id": "case-1"}
        mock_msg.data.decode.return_value = _enveloped_json(
            event_type="context.rehydrate.request",
            payload=rehydrate_payload,
            entity_id="case-1",
        )
        mock_msg.ack = AsyncMock()

        mock_request = MagicMock()
        mock_protobuf_mapper.to_rehydrate_session_request.return_value = mock_request

        mock_grpc_context = MagicMock()
        mock_context.return_value = mock_grpc_context

        mock_response = MagicMock()
        mock_response.packs = []
        mock_service.RehydrateSession = AsyncMock(return_value=mock_response)

        mock_response_dto = MagicMock()
        mock_response_mapper.to_rehydrate_session_response_dto.return_value = mock_response_dto

        mock_uc = AsyncMock()
        handler._publish_rehydrate_response_uc = mock_uc
        handler._connected = True

        await handler._handle_rehydrate_request(mock_msg)

        mock_protobuf_mapper.to_rehydrate_session_request.assert_called_once()
        mock_service.RehydrateSession.assert_awaited_once()
        mock_error_handler.check_and_raise.assert_called_once()
        mock_response_mapper.to_rehydrate_session_response_dto.assert_called_once()
        mock_uc.execute.assert_awaited_once_with(mock_response_dto)
        mock_msg.ack.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("services.context.nats_handler.NatsProtobufMapper")
    async def test_handle_rehydrate_request_acks_invalid_envelope(
        self,
        mock_protobuf_mapper: MagicMock,
    ) -> None:
        """Test invalid non-enveloped payload is dropped (ACK, no processing)."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_msg = MagicMock()
        mock_msg.data.decode.return_value = json.dumps({"case_id": "case-1"})
        mock_msg.ack = AsyncMock()
        mock_msg.nak = AsyncMock()

        await handler._handle_rehydrate_request(mock_msg)

        mock_protobuf_mapper.to_rehydrate_session_request.assert_not_called()
        mock_msg.ack.assert_awaited_once()
        mock_msg.nak.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_rehydrate_request_naks_on_error(self) -> None:
        """Test rehydrate request sends NAK on error."""
        mock_service = MagicMock()
        handler = ContextNATSHandler(nats_url="nats://localhost:4222", context_service=mock_service)

        mock_msg = MagicMock()
        mock_msg.data.decode.side_effect = ValueError("Invalid JSON")
        mock_msg.nak = AsyncMock()

        await handler._handle_rehydrate_request(mock_msg)

        mock_msg.nak.assert_awaited_once()
