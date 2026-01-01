"""NATS messaging adapter implementing MessagingPort.

Infrastructure layer adapter that publishes messages to NATS JetStream.
Following Hexagonal Architecture: implements MessagingPort interface.
"""

import asyncio
import json
import logging

from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
)
from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)
from core.context.ports.messaging_port import MessagingPort
from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NatsMessagingAdapter(MessagingPort):
    """NATS adapter for publishing messages.

    Implements MessagingPort interface using NATS JetStream.
    Infrastructure concern: handles NATS protocol details.
    """

    def __init__(self, jetstream: JetStreamContext) -> None:
        """Initialize adapter with NATS JetStream context.

        Args:
            jetstream: NATS JetStream context for publishing
        """
        self._js = jetstream

    async def publish_update_context_response(
        self, response: UpdateContextResponseDTO
    ) -> None:
        """Publish UpdateContext response to NATS with EventEnvelope.

        Args:
            response: UpdateContext response DTO

        Raises:
            RuntimeError: If publishing fails
        """
        try:
            payload = {
                "story_id": response.story_id,
                "status": response.status,
                "version": response.version,
                "hash": response.hash,
                "warnings": response.warnings,
            }

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="context.update.response",
                payload=payload,
                producer="context-service",
                entity_id=response.story_id,
                operation="update_response",
            )

            # Serialize envelope to JSON using infrastructure mapper
            await self._js.publish(
                "context.update.response",
                json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode(),
            )

            logger.info(
                f"Published update context response: story_id={response.story_id}, "
                f"version={response.version}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish update context response: {e}", exc_info=True)
            raise RuntimeError(f"Failed to publish update context response: {e}") from e

    async def publish_rehydrate_session_response(
        self, response: RehydrateSessionResponseDTO
    ) -> None:
        """Publish RehydrateSession response to NATS with EventEnvelope.

        Args:
            response: RehydrateSession response DTO

        Raises:
            RuntimeError: If publishing fails
        """
        try:
            payload = {
                "case_id": response.case_id,
                "status": response.status,
                "generated_at_ms": response.generated_at_ms,
                "packs_count": response.packs_count,
                "stats": {
                    "decisions": response.stats.decisions,
                    "decision_edges": response.stats.decision_edges,
                    "impacts": response.stats.impacts,
                    "events": response.stats.events,
                    "roles": response.stats.roles,
                },
            }

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="context.rehydrate.response",
                payload=payload,
                producer="context-service",
                entity_id=response.case_id,
                operation="rehydrate_response",
            )

            # Serialize envelope to JSON using infrastructure mapper
            await self._js.publish(
                "context.rehydrate.response",
                json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode(),
            )

            logger.info(
                f"Published rehydrate session response: case_id={response.case_id}, "
                f"packs={response.packs_count}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish rehydrate session response: {e}", exc_info=True
            )
            raise RuntimeError(
                f"Failed to publish rehydrate session response: {e}"
            ) from e

    async def publish_context_updated(self, story_id: str, version: int) -> None:
        """Publish context updated event to NATS with EventEnvelope.

        Args:
            story_id: Story identifier
            version: Context version number

        Raises:
            RuntimeError: If publishing fails
        """
        try:
            payload = {
                "story_id": story_id,
                "version": version,
                "timestamp": asyncio.get_event_loop().time(),
            }

            # Create event envelope with idempotency key
            envelope = create_event_envelope(
                event_type="context.updated",
                payload=payload,
                producer="context-service",
                entity_id=story_id,
                operation="context_updated",
            )

            # Serialize envelope to JSON using infrastructure mapper
            await self._js.publish(
                "context.events.updated",
                json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode(),
            )

            logger.info(
                f"Published context.updated event: story_id={story_id}, version={version}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish context.updated event: {e}", exc_info=True)
            raise RuntimeError(f"Failed to publish context.updated event: {e}") from e

