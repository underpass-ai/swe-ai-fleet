"""
NATS event handler for Context Service.
Handles asynchronous context updates via NATS messaging.
"""

import asyncio
import json
import logging
from typing import Any

import nats
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig

logger = logging.getLogger(__name__)


class ContextNATSHandler:
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
        self.nats_url = nats_url
        self.context_service = context_service
        self.nc: NATS | None = None
        self.js = None

    async def connect(self):
        """Connect to NATS and setup JetStream."""
        try:
            logger.info(f"Connecting to NATS at {self.nats_url}")
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()

            # Ensure stream exists
            await self._ensure_stream()

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
        if not self.nc or not self.js:
            raise RuntimeError("Not connected to NATS")

        # Subscribe to context update requests
        await self.js.subscribe(
            "context.update.request",
            cb=self._handle_update_request,
            durable="context-update-handler",
        )

        # Subscribe to rehydration requests
        await self.js.subscribe(
            "context.rehydrate.request",
            cb=self._handle_rehydrate_request,
            durable="context-rehydrate-handler",
        )

        logger.info("✓ Subscribed to NATS subjects")

    async def _handle_update_request(self, msg):
        """Handle context update request from NATS."""
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Received update request: story_id={data.get('story_id')}")

            # Process update
            # TODO: Convert to gRPC request and call context_service.UpdateContext
            
            # Publish response
            response = {
                "story_id": data.get("story_id"),
                "status": "success",
                "version": 1,
            }
            
            await self.js.publish(
                "context.update.response",
                json.dumps(response).encode(),
            )

            await msg.ack()
            logger.info(f"✓ Processed update request: {data.get('story_id')}")

        except Exception as e:
            logger.error(f"Error handling update request: {e}", exc_info=True)
            await msg.nak()

    async def _handle_rehydrate_request(self, msg):
        """Handle session rehydration request from NATS."""
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Received rehydrate request: case_id={data.get('case_id')}")

            # Process rehydration
            # TODO: Convert to gRPC request and call context_service.RehydrateSession
            
            # Publish response
            response = {
                "case_id": data.get("case_id"),
                "status": "success",
            }
            
            await self.js.publish(
                "context.rehydrate.response",
                json.dumps(response).encode(),
            )

            await msg.ack()
            logger.info(f"✓ Processed rehydrate request: {data.get('case_id')}")

        except Exception as e:
            logger.error(f"Error handling rehydrate request: {e}", exc_info=True)
            await msg.nak()

    async def publish_context_updated(self, story_id: str, version: int):
        """Publish context updated event."""
        if not self.js:
            logger.warning("NATS not connected, skipping event publish")
            return

        try:
            event = {
                "event_type": "context.updated",
                "story_id": story_id,
                "version": version,
                "timestamp": asyncio.get_event_loop().time(),
            }

            await self.js.publish(
                "context.events.updated",
                json.dumps(event).encode(),
            )

            logger.info(f"✓ Published context.updated event: {story_id}")

        except Exception as e:
            logger.error(f"Error publishing event: {e}")

    async def close(self):
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            logger.info("✓ NATS connection closed")

