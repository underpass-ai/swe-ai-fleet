"""NATS publisher adapter implementation."""

import json
import logging
import time

from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
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
        """Publish streaming event to NATS with EventEnvelope.

        Implements NATSPublisherPort.publish_stream_event()
        """
        if not self._js:
            logger.warning("NATS not connected, skipping stream event publish")
            return

        try:
            payload = {
                "type": event_type,
                "agent_id": agent_id,
                "timestamp": time.time(),
                **data,
            }

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type=f"vllm.streaming.{event_type}",
                payload=payload,
                producer="ray-executor-service",
                entity_id=agent_id,
                operation="stream_event",
            )

            subject = f"vllm.streaming.{agent_id}"
            await self._js.publish(
                subject, json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
            )

            logger.info(
                f"✓ Published stream event: {event_type} to {subject}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

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
        """Publish deliberation completion result to NATS with EventEnvelope.

        Implements NATSPublisherPort.publish_deliberation_result()
        """
        if not self._js:
            logger.warning("NATS not connected, skipping result publish")
            return

        try:
            payload = {
                "deliberation_id": deliberation_id,
                "task_id": task_id,
                "status": status,
                "timestamp": time.time(),
            }

            if result:
                payload["result"] = result
            if error:
                payload["error"] = error

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="deliberation.completed",
                payload=payload,
                producer="ray-executor-service",
                entity_id=deliberation_id,
                operation="deliberation_result",
            )

            subject = "orchestration.deliberation.completed"
            await self._js.publish(
                subject, json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
            )

            logger.info(
                f"✓ Published deliberation result: {deliberation_id} ({status}), "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to publish deliberation result: {e}")
            # Raise here since result publishing is critical
            raise

