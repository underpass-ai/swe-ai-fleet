"""NATS implementation of MessagingPort.

This adapter provides a NATS JetStream implementation of the MessagingPort,
allowing domain logic to publish and subscribe to events without depending on NATS.

Following Hexagonal Architecture:
- Implements MessagingPort from domain/ports/
- NATS-specific logic contained here
- Can be swapped with Kafka/RabbitMQ adapter without changing domain
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import nats
from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext
from services.orchestrator.domain.events import DomainEvent
from services.orchestrator.domain.ports import MessagingError, MessagingPort
from services.orchestrator.domain.ports.pull_subscription_port import PullSubscriptionPort
from services.orchestrator.infrastructure.adapters.nats_pull_subscription_adapter import (
    NATSPullSubscriptionAdapter,
)

logger = logging.getLogger(__name__)

# Constants
_NOT_CONNECTED_ERROR = "Not connected to NATS. Call connect() first."


class NATSMessagingAdapter(MessagingPort):
    """NATS JetStream implementation of MessagingPort.

    This adapter wraps NATS JetStream client and provides the MessagingPort
    interface for publishing and subscribing to events.

    Attributes:
        nats_url: NATS server URL
        nc: NATS client connection
        js: JetStream context
    """

    def __init__(self, nats_url: str):
        """Initialize NATS messaging adapter.

        Args:
            nats_url: NATS server URL (e.g., "nats://localhost:4222")
        """
        self.nats_url = nats_url
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self) -> None:
        """Connect to NATS and setup JetStream.

        Raises:
            MessagingError: If connection fails
        """
        try:
            logger.info(f"Connecting to NATS at {self.nats_url}")
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info("✓ Connected to NATS successfully")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise MessagingError(f"NATS connection failed: {e}", cause=e) from e

    async def publish(self, subject: str, event: DomainEvent) -> None:
        """Publish a domain event to a NATS subject with EventEnvelope.

        Args:
            subject: NATS subject (e.g., "orchestration.task.completed")
            event: Domain event to publish

        Raises:
            MessagingError: If publishing fails or not connected
        """
        if not self.js:
            raise MessagingError(_NOT_CONNECTED_ERROR)

        try:
            # Convert event to dict (legacy DomainEvent.to_dict() - will be refactored later)
            event_dict = event.to_dict()

            # Extract entity_id from event payload for idempotency key
            # Try common fields: task_id, story_id, deliberation_id, etc.
            entity_id = (
                event_dict.get("task_id")
                or event_dict.get("story_id")
                or event_dict.get("deliberation_id")
                or event_dict.get("agent_id")
                or "unknown"
            )

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type=event.event_type,
                payload=event_dict,
                producer="orchestrator-service",
                entity_id=str(entity_id),
                operation="publish",
                correlation_id=event_dict.get("correlation_id"),  # Preserve if present
            )

            # Serialize envelope to JSON using infrastructure mapper
            payload = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()

            await self.js.publish(subject, payload)
            logger.info(
                f"✓ Published {event.event_type} to {subject}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            raise MessagingError(
                f"Failed to publish event to {subject}", cause=e
            ) from e

    async def subscribe(
        self,
        subject: str,
        handler: Callable,
        queue_group: str | None = None,
        durable: str | None = None,
    ) -> None:
        """Subscribe to messages on a NATS subject (PUSH consumer).

        Args:
            subject: NATS subject to subscribe to
            handler: Async callback to handle messages
            queue_group: Optional queue group for load balancing
            durable: Optional durable name for resumable subscriptions

        Raises:
            MessagingError: If subscription fails or not connected
        """
        if not self.js:
            raise MessagingError(_NOT_CONNECTED_ERROR)

        try:
            await self.js.subscribe(
                subject=subject,
                cb=handler,
                queue=queue_group,
                durable=durable,
                manual_ack=True,
            )
            logger.info(f"✓ Subscribed to {subject}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            raise MessagingError(
                f"Failed to subscribe to {subject}", cause=e
            ) from e

    async def pull_subscribe(
        self,
        subject: str,
        durable: str,
        stream: str,
    ) -> PullSubscriptionPort:
        """Create a PULL subscription for load-balanced consumption.

        Pull subscriptions are preferred in Kubernetes for multi-pod deployments
        as they allow multiple consumers to share work efficiently.

        Args:
            subject: NATS subject to subscribe to
            durable: Durable consumer name (for resumable subscriptions)
            stream: Stream name containing the subject

        Returns:
            PullSubscriptionPort adapter wrapping NATS subscription

        Raises:
            MessagingError: If subscription fails or not connected
        """
        if not self.js:
            raise MessagingError(_NOT_CONNECTED_ERROR)

        try:
            nats_subscription = await self.js.pull_subscribe(
                subject=subject,
                durable=durable,
                stream=stream,
            )
            logger.info(f"✓ Pull subscription created: {subject} (durable: {durable})")

            # Wrap NATS subscription in port adapter
            return NATSPullSubscriptionAdapter(nats_subscription, subject)

        except Exception as e:
            logger.error(f"Failed to create pull subscription for {subject}: {e}")
            raise MessagingError(
                f"Failed to pull_subscribe to {subject}", cause=e
            ) from e

    async def close(self) -> None:
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            logger.info("✓ NATS connection closed")
