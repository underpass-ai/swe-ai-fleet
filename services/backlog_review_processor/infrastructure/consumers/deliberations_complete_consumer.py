"""Consumer for planning.backlog_review.deliberations.complete events.

Inbound Adapter (Infrastructure):
- Listens to planning.backlog_review.deliberations.complete NATS events
- Published by Planning Service when all role deliberations for a story are complete
- Triggers task extraction from agent deliberations
"""

import asyncio
import json
import logging

from backlog_review_processor.application.usecases.extract_tasks_from_deliberations_usecase import (
    ExtractTasksFromDeliberationsUseCase,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_durable import NATSDurable
from backlog_review_processor.domain.value_objects.nats_stream import NATSStream
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from core.shared.events.infrastructure import parse_required_envelope

logger = logging.getLogger(__name__)


class DeliberationsCompleteConsumer:
    """Consumer for deliberations complete events.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to planning.backlog_review.deliberations.complete (NATS)
    - Delegates to ExtractTasksFromDeliberationsUseCase

    Responsibilities (ONLY):
    - NATS subscription management
    - Message polling
    - DTO parsing (NATS → domain VOs)
    - ACK/NAK handling
    - Delegation to use case

    NOT responsible for:
    - Business logic (use case)
    - Task extraction (use case)
    """

    def __init__(
        self,
        nats_client,
        jetstream,
        extract_tasks_usecase: ExtractTasksFromDeliberationsUseCase,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            extract_tasks_usecase: Use case for extracting tasks from deliberations
        """
        self._nc = nats_client
        self._js = jetstream
        self._extract_tasks = extract_tasks_usecase
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming planning.backlog_review.deliberations.complete events."""
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.DELIBERATIONS_COMPLETE),
                durable=str(NATSDurable.DELIBERATIONS_COMPLETE),
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info(
                "✓ DeliberationsCompleteConsumer: subscription created (DURABLE)"
            )

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start DeliberationsCompleteConsumer: {e}", exc_info=True
            )
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 DeliberationsCompleteConsumer: polling started")

        while True:
            try:
                msgs = await self._subscription.fetch(batch=1, timeout=5)

                for msg in msgs:
                    await self._handle_message(msg)

            except TimeoutError:
                continue

            except Exception as e:
                logger.error(f"Error polling messages: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _handle_message(self, msg) -> None:
        """Handle planning.backlog_review.deliberations.complete message.

        Responsibilities:
        - Parse NATS message (DTO)
        - Extract envelope fields (idempotency_key, correlation_id)
        - Extract ceremony_id, story_id, agent_deliberations from payload
        - Delegate to use case
        - ACK/NAK
        """
        try:
            # 1. Parse JSON payload (DTO - external format)
            data = json.loads(msg.data.decode())

            # 2. Require EventEnvelope (no legacy fallback)
            envelope = parse_required_envelope(data)
            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            payload = envelope.payload

            logger.info(
                f"📥 [EventEnvelope] Received event with envelope: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            ceremony_id_str = payload.get("ceremony_id", "")
            story_id_str = payload.get("story_id", "")
            agent_deliberations = payload.get("agent_deliberations", [])

            if not ceremony_id_str or not story_id_str:
                logger.error(
                    f"Missing ceremony_id or story_id in payload: {payload}"
                )
                await msg.nak()
                return

            ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
            story_id = StoryId(story_id_str)

            logger.info(
                f"📥 Received deliberations complete event: "
                f"ceremony={ceremony_id.value}, story={story_id.value}, "
                f"num_deliberations={len(agent_deliberations)}, "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # 2. Delegate to use case
            await self._extract_tasks.execute(
                ceremony_id=ceremony_id,
                story_id=story_id,
                agent_deliberations=agent_deliberations,
            )

            # 3. ACK message (success)
            await msg.ack()

            logger.info(
                f"✅ Task extraction triggered for story {story_id.value} "
                f"in ceremony {ceremony_id.value}"
            )

        except ValueError as e:
            # Invalid envelope / invalid payload: permanent format error (drop).
            logger.error(f"Dropping invalid deliberations complete event: {e}", exc_info=True)
            await msg.ack()

        except Exception as e:
            # Unexpected error - retry
            logger.error(f"Error handling deliberations complete event: {e}", exc_info=True)
            await msg.nak()

    async def stop(self) -> None:
        """Stop consumer and cleanup."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("DeliberationsCompleteConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("DeliberationsCompleteConsumer stopped")

