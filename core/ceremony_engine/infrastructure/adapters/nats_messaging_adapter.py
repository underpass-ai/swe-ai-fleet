"""NATS Messaging Adapter for Ceremony Engine.

Following Hexagonal Architecture:
- Implements MessagingPort (application layer interface)
- Lives in infrastructure layer
- Handles NATS JetStream publishing with EventEnvelope
"""

import json
import logging

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure.event_envelope_mapper import EventEnvelopeMapper
from nats.aio.client import Client
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """NATS messaging adapter for Ceremony Engine.

    Adapter responsibilities:
    - Connect to NATS JetStream
    - Implement MessagingPort interface
    - Publish events with EventEnvelope to NATS subjects
    - Handle NATS errors

    Following Hexagonal Architecture:
    - Implements port (interface) from application layer
    - Uses NATS client (infrastructure detail)
    - Uses EventEnvelopeMapper for serialization (infrastructure)

    Business Rules:
    - All events MUST include idempotency_key (enforced by EventEnvelope)
    - All events MUST include correlation_id (enforced by EventEnvelope)
    - Events are published to NATS JetStream for durability
    """

    def __init__(
        self,
        nats_client: Client,
        jetstream: JetStreamContext,
    ) -> None:
        """Initialize adapter with NATS configuration.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context

        Raises:
            ValueError: If nats_client or jetstream is None (fail-fast)
        """
        if not nats_client:
            raise ValueError("nats_client is required (fail-fast)")
        if not jetstream:
            raise ValueError("jetstream is required (fail-fast)")

        self._nc = nats_client
        self._js = jetstream

        logger.info("NATSMessagingAdapter initialized for Ceremony Engine")

    async def publish_event(
        self,
        subject: str,
        envelope: EventEnvelope,
    ) -> None:
        """Publish an event with EventEnvelope to NATS JetStream.

        Args:
            subject: NATS subject (e.g., "ceremony.sprint_planning.started")
            envelope: Event envelope with idempotency_key, correlation_id, etc.

        Raises:
            ValueError: If subject or envelope is invalid
            RuntimeError: If publish fails
        """
        if not subject or not subject.strip():
            raise ValueError("subject cannot be empty (fail-fast)")

        if not envelope:
            raise ValueError("envelope cannot be None (fail-fast)")

        try:
            # Serialize envelope to JSON using infrastructure mapper
            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

            # Publish to JetStream
            ack = await self._js.publish(subject, message)

            logger.info(
                f"✅ Published event to {subject}: "
                f"stream={ack.stream}, sequence={ack.seq}, "
                f"event_type={envelope.event_type}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

        except Exception as e:
            error_msg = f"Failed to publish event to {subject}: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
