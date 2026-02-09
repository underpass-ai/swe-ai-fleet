"""NATS Messaging Adapter for Task Extraction Service.

Following Hexagonal Architecture:
- Implements MessagingPort (application layer interface)
- Lives in infrastructure layer
- Handles NATS JetStream publishing
"""

import json
import logging

from backlog_review_processor.application.ports.messaging_port import MessagingPort
from core.shared.events import create_event_envelope
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
        """Publish an event to NATS JetStream with EventEnvelope.

        Args:
            subject: NATS subject
            payload: Event payload (dict)

        Raises:
            RuntimeError: If publish fails
        """
        try:
            entity_id = (
                payload.get("ceremony_id")
                or payload.get("story_id")
                or payload.get("task_id")
                or payload.get("deliberation_id")
                or "unknown"
            )
            operation = payload.get("operation")

            envelope = create_event_envelope(
                event_type=subject,
                payload=payload,
                producer="backlog-review-processor",
                entity_id=str(entity_id),
                operation=operation if isinstance(operation, str) else None,
            )

            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

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
