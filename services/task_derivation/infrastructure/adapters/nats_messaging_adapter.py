"""NATS adapter for publishing task-derivation events, implementing MessagingPort."""

from __future__ import annotations

import json
import logging
from typing import Any

from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from task_derivation.application.ports.messaging_port import MessagingPort
from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.infrastructure.mappers.nats_event_mapper import NatsEventMapper

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """Concrete adapter for publishing task-derivation domain events to NATS."""

    def __init__(self, nats_client: Any) -> None:
        """Initialize adapter with NATS client.

        Args:
            nats_client: Connected nats.aio.client.Client instance

        Raises:
            ValueError: If nats_client is None
        """
        if not nats_client:
            raise ValueError("nats_client cannot be None")

        self._nats_client = nats_client

    async def publish_task_derivation_completed(
        self,
        event: TaskDerivationCompletedEvent,
    ) -> None:
        """Publish task derivation success event to NATS with EventEnvelope.

        Args:
            event: TaskDerivationCompletedEvent with task nodes and dependencies

        Raises:
            Exception: If NATS publish fails
        """
        try:
            # Map domain event to infrastructure DTO
            payload_dto = NatsEventMapper.to_completed_payload(event)

            # Convert DTO to dict
            payload_dict = NatsEventMapper.payload_to_dict(payload_dto)

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="task.derivation.completed",
                payload=payload_dict,
                producer="task-derivation-service",
                entity_id=event.plan_id.value,
                operation="task_derivation_completed",
            )

            # Serialize envelope to JSON using infrastructure mapper
            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

            # Publish to NATS
            await self._nats_client.publish("task.derivation.completed", message)

            logger.info(
                "Published task.derivation.completed for plan %s (tasks: %d), "
                "idempotency_key=%s..., correlation_id=%s",
                event.plan_id.value,
                event.task_count,
                envelope.idempotency_key[:16],
                envelope.correlation_id,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish task.derivation.completed event: %s",
                exc,
                exc_info=True,
            )
            raise

    async def publish_task_derivation_failed(
        self,
        event: TaskDerivationFailedEvent,
    ) -> None:
        """Publish task derivation failure event to NATS with EventEnvelope.

        Args:
            event: TaskDerivationFailedEvent with failure reason

        Raises:
            Exception: If NATS publish fails
        """
        try:
            # Map domain event to infrastructure DTO
            payload_dto = NatsEventMapper.to_failed_payload(event)

            # Convert DTO to dict
            payload_dict = NatsEventMapper.payload_to_dict(payload_dto)

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="task.derivation.failed",
                payload=payload_dict,
                producer="task-derivation-service",
                entity_id=event.plan_id.value,
                operation="task_derivation_failed",
            )

            # Serialize envelope to JSON using infrastructure mapper
            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

            # Publish to NATS
            await self._nats_client.publish("task.derivation.failed", message)

            logger.warning(
                "Published task.derivation.failed for plan %s: %s, "
                "idempotency_key=%s..., correlation_id=%s",
                event.plan_id.value,
                event.reason,
                envelope.idempotency_key[:16],
                envelope.correlation_id,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish task.derivation.failed event: %s",
                exc,
                exc_info=True,
            )
            raise

