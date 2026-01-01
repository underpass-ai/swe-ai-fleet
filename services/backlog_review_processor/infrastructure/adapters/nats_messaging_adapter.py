"""NATS Messaging Adapter for Task Extraction Service.

Following Hexagonal Architecture:
- Implements MessagingPort (application layer interface)
- Lives in infrastructure layer
- Handles NATS JetStream publishing
"""

import json
import logging

from backlog_review_processor.application.ports.messaging_port import MessagingPort
from core.shared.events import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from nats.aio.client import Client
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """NATS messaging adapter for Task Extraction Service.

    Adapter responsibilities:
    - Connect to NATS JetStream
    - Implement MessagingPort interface
    - Publish events to NATS subjects
    - Handle NATS errors

    Following Hexagonal Architecture:
    - Implements port (interface) from application layer
    - Uses NATS client (infrastructure detail)
    """

    def __init__(
        self,
        nats_client: Client,
        jetstream: JetStreamContext,
    ):
        """Initialize adapter with NATS configuration.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
        """
        self._nc = nats_client
        self._js = jetstream

        logger.info("NATSMessagingAdapter initialized")

    async def publish_event(self, subject: str, payload: dict) -> None:
        """Publish an event to NATS JetStream (legacy, without envelope).

        DEPRECATED: Use publish_event_with_envelope() for new code.

        Args:
            subject: NATS subject
            payload: Event payload (dict)

        Raises:
            RuntimeError: If publish fails
        """
        try:
            # Serialize payload to JSON
            message = json.dumps(payload).encode("utf-8")

            # Publish to JetStream
            ack = await self._js.publish(subject, message)
            logger.info(
                f"✅ Published event to {subject}: "
                f"stream={ack.stream}, sequence={ack.seq}"
            )

        except Exception as e:
            error_msg = f"Failed to publish event to {subject}: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    async def publish_event_with_envelope(
        self,
        subject: str,
        envelope: EventEnvelope,
    ) -> None:
        """Publish an event with EventEnvelope to NATS JetStream.

        Args:
            subject: NATS subject
            envelope: Event envelope with idempotency_key, correlation_id, etc.

        Raises:
            RuntimeError: If publish fails
        """
        try:
            # Serialize envelope to JSON using infrastructure mapper
            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

            # Publish to JetStream
            ack = await self._js.publish(subject, message)

            logger.info(
                f"✅ Published event to {subject}: "
                f"stream={ack.stream}, sequence={ack.seq}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

        except Exception as e:
            error_msg = f"Failed to publish event to {subject}: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
