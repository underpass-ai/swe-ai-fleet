"""NATS publisher adapter implementation."""

import json
import logging
import time

from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NATSPublisherAdapter:
    """Adapter for NATS event publishing.

    This adapter implements NATSPublisherPort using NATS JetStream.

    Following Hexagonal Architecture:
    - Implements port (interface) defined in domain
    - Translates domain events to NATS messages
    - Handles NATS-specific errors
    """

    def __init__(self, jetstream: JetStreamContext | None):
        """Initialize NATS publisher adapter.

        Args:
            jetstream: NATS JetStream context (optional)
        """
        self._js = jetstream

    async def publish_stream_event(
        self,
        event_type: str,
        agent_id: str,
        data: dict[str, any],
    ) -> None:
        """Publish streaming event to NATS.

        Implements NATSPublisherPort.publish_stream_event()
        """
        if not self._js:
            logger.warning("NATS not connected, skipping stream event publish")
            return

        try:
            event = {
                "type": event_type,
                "agent_id": agent_id,
                "timestamp": time.time(),
                **data,
            }

            subject = f"vllm.streaming.{agent_id}"
            await self._js.publish(subject, json.dumps(event).encode())

            logger.debug(f"✓ Published stream event: {event_type} to {subject}")

        except Exception as e:
            logger.warning(f"Failed to publish stream event: {e}")
            # Don't raise - streaming is optional

    async def publish_deliberation_result(
        self,
        deliberation_id: str,
        task_id: str,
        status: str,
        result: dict[str, any] | None = None,
        error: str | None = None,
    ) -> None:
        """Publish deliberation completion result to NATS.

        Implements NATSPublisherPort.publish_deliberation_result()
        """
        if not self._js:
            logger.warning("NATS not connected, skipping result publish")
            return

        try:
            event = {
                "event_type": "deliberation.completed",
                "deliberation_id": deliberation_id,
                "task_id": task_id,
                "status": status,
                "timestamp": time.time(),
            }

            if result:
                event["result"] = result
            if error:
                event["error"] = error

            subject = "orchestration.deliberation.completed"
            await self._js.publish(subject, json.dumps(event).encode())

            logger.info(f"✓ Published deliberation result: {deliberation_id} ({status})")

        except Exception as e:
            logger.error(f"Failed to publish deliberation result: {e}")
            # Raise here since result publishing is critical
            raise

