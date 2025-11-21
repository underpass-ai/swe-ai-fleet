"""
NATS event handler for Context Service.
Handles asynchronous context updates via NATS messaging.
"""

import json
import logging
from typing import Any

import nats
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig

from core.context.application.usecases.publish_context_updated import (
    PublishContextUpdatedUseCase,
)
from core.context.application.usecases.publish_rehydrate_session_response import (
    PublishRehydrateSessionResponseUseCase,
)
from core.context.application.usecases.publish_update_context_response import (
    PublishUpdateContextResponseUseCase,
)

from services.context.infrastructure.adapters.connection_state_base import (
    ConnectionStateBase,
)
from services.context.infrastructure.adapters.internal_servicer_context import (
    InternalServicerContext,
)
from services.context.infrastructure.adapters.nats_messaging_adapter import (
    NatsMessagingAdapter,
)
from services.context.infrastructure.adapters.servicer_context_error_handler import (
    ServicerContextErrorHandler,
)
from services.context.infrastructure.mappers.nats_protobuf_mapper import (
    NatsProtobufMapper,
)
from services.context.infrastructure.mappers.protobuf_response_mapper import (
    ProtobufResponseMapper,
)

logger = logging.getLogger(__name__)

_NOT_CONNECTED_ERROR = "NATS not connected - call connect() first"


class ContextNATSHandler(ConnectionStateBase):
    """Handles NATS messaging for Context Service."""

    def __init__(
        self,
        nats_url: str,
        context_service: Any,
    ):
        """
        Initialize NATS handler.

        Args:
            nats_url: NATS server URL
            context_service: ContextServiceServicer instance
        """
        super().__init__()
        self.nats_url = nats_url
        self.context_service = context_service

    @property
    def nc(self) -> NATS:
        """Get NATS client connection.

        Returns:
            NATS client

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._nc

    @property
    def js(self):
        """Get NATS JetStream context.

        Returns:
            JetStream context

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._js

    @property
    def messaging(self) -> NatsMessagingAdapter:
        """Get messaging adapter.

        Returns:
            Messaging adapter

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._messaging

    @property
    def publish_context_updated_uc(self) -> PublishContextUpdatedUseCase:
        """Get publish context updated use case.

        Returns:
            Use case instance

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._publish_context_updated_uc

    @property
    def publish_update_response_uc(self) -> PublishUpdateContextResponseUseCase:
        """Get publish update response use case.

        Returns:
            Use case instance

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._publish_update_response_uc

    @property
    def publish_rehydrate_response_uc(self) -> PublishRehydrateSessionResponseUseCase:
        """Get publish rehydrate response use case.

        Returns:
            Use case instance

        Raises:
            RuntimeError: If not connected
        """
        self._require_connected(_NOT_CONNECTED_ERROR)
        return self._publish_rehydrate_response_uc

    async def connect(self):
        """Connect to NATS and setup JetStream."""
        try:
            logger.info(f"Connecting to NATS at {self.nats_url}")
            self._nc = await nats.connect(self.nats_url)
            self._js = self._nc.jetstream()

            # Initialize messaging adapter
            self._messaging = NatsMessagingAdapter(self._js)

            # Initialize use cases with messaging port
            self._publish_context_updated_uc = PublishContextUpdatedUseCase(self._messaging)
            self._publish_update_response_uc = PublishUpdateContextResponseUseCase(self._messaging)
            self._publish_rehydrate_response_uc = PublishRehydrateSessionResponseUseCase(
                self._messaging
            )

            # Ensure stream exists
            await self._ensure_stream()

            self._connected = True
            logger.info("✓ Connected to NATS successfully")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def _ensure_stream(self):
        """Ensure NATS JetStream stream exists."""
        try:
            stream_config = StreamConfig(
                name="CONTEXT",
                subjects=["context.>"],
                description="Context service events",
            )
            await self.js.add_stream(stream_config)
            logger.info("✓ NATS stream 'CONTEXT' ready")
        except Exception as e:
            # Stream might already exist
            logger.debug(f"Stream creation: {e}")

    async def subscribe(self):
        """Subscribe to context-related events."""
        if not self._is_connected():
            raise RuntimeError("Not connected to NATS - call connect() first")

        # Subscribe to context update requests with queue group for load balancing
        # NOTE: Don't use 'durable' with 'queue' - they conflict in nats-py
        await self.js.subscribe(
            "context.update.request",
            cb=self._handle_update_request,
            queue="context-workers",  # Queue group for load balancing
        )

        # Subscribe to rehydration requests with queue group for load balancing
        await self.js.subscribe(
            "context.rehydrate.request",
            cb=self._handle_rehydrate_request,
            queue="context-workers",  # Queue group for load balancing
        )

        logger.info("✓ Subscribed to NATS subjects")

    async def _handle_update_request(self, msg):
        """Handle context update request from NATS."""
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Received update request: story_id={data.get('story_id')}")

            # Convert JSON to protobuf UpdateContextRequest using mapper
            request = NatsProtobufMapper.to_update_context_request(data)

            # Create internal servicer context (not a mock - real implementation)
            grpc_context = InternalServicerContext()

            # Call context service UpdateContext method
            update_response = await self.context_service.UpdateContext(request, grpc_context)

            # Check if servicer set an error (servicer methods catch exceptions and set error codes)
            ServicerContextErrorHandler.check_and_raise(grpc_context, "UpdateContext")

            # Convert protobuf response to DTO
            response_dto = ProtobufResponseMapper.to_update_context_response_dto(
                update_response, data.get("story_id", "")
            )

            # Publish response using use case
            await self.publish_update_response_uc.execute(response_dto)

            await msg.ack()
            logger.info(
                f"✓ Processed update request: story_id={data.get('story_id')}, "
                f"version={update_response.version}"
            )

        except Exception as e:
            logger.error(f"Error handling update request: {e}", exc_info=True)
            await msg.nak()

    async def _handle_rehydrate_request(self, msg):
        """Handle session rehydration request from NATS."""
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Received rehydrate request: case_id={data.get('case_id')}")

            # Convert JSON to protobuf RehydrateSessionRequest using mapper
            request = NatsProtobufMapper.to_rehydrate_session_request(data)

            # Create internal servicer context (not a mock - real implementation)
            grpc_context = InternalServicerContext()

            # Call context service RehydrateSession method
            rehydrate_response = await self.context_service.RehydrateSession(request, grpc_context)

            # Check if servicer set an error (servicer methods catch exceptions and set error codes)
            ServicerContextErrorHandler.check_and_raise(grpc_context, "RehydrateSession")

            # Convert protobuf response to DTO
            response_dto = ProtobufResponseMapper.to_rehydrate_session_response_dto(
                rehydrate_response
            )

            # Publish response using use case
            await self.publish_rehydrate_response_uc.execute(response_dto)

            await msg.ack()
            logger.info(
                f"✓ Processed rehydrate request: case_id={data.get('case_id')}, "
                f"packs={len(rehydrate_response.packs)}"
            )

        except Exception as e:
            logger.error(f"Error handling rehydrate request: {e}", exc_info=True)
            await msg.nak()

    async def publish_context_updated(self, story_id: str, version: int):
        """Publish context updated event."""
        if not self._is_connected():
            logger.warning("NATS not connected, skipping event publish")
            return

        await self.publish_context_updated_uc.execute(story_id, version)

    async def _close_connection(self) -> None:
        """Close NATS connection."""
        await self._nc.close()
        logger.info("✓ NATS connection closed")

