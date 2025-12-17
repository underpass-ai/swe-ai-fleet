"""Consumer for planning.backlog_review.deliberations.complete events.

Inbound Adapter (Infrastructure):
- Listens to planning.backlog_review.deliberations.complete NATS events
- Published by Task Extraction Service when all role deliberations for a story are complete
- Updates ceremony progress in Planning Service
"""

import asyncio
import json
import logging

from nats.aio.client import Client
from nats.js import JetStreamContext
from planning.application.ports.storage_port import StoragePort
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject

logger = logging.getLogger(__name__)


class DeliberationsCompleteProgressConsumer:
    """Consumer for deliberations complete events to track progress.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to planning.backlog_review.deliberations.complete (NATS)
    - Updates ceremony progress in storage

    Responsibilities (ONLY):
    - NATS subscription management
    - Message polling
    - DTO parsing (NATS → domain VOs)
    - Update ceremony progress
    - ACK/NAK handling
    """

    def __init__(
        self,
        nats_client: Client,
        jetstream: JetStreamContext,
        storage: StoragePort,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            storage: Storage port for updating ceremony progress
        """
        self._nc = nats_client
        self._js = jetstream
        self._storage = storage
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming planning.backlog_review.deliberations.complete events."""
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.DELIBERATIONS_COMPLETE),
                durable="planning-deliberations-complete-progress",
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info(
                "✓ DeliberationsCompleteProgressConsumer: subscription created (DURABLE)"
            )

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start DeliberationsCompleteProgressConsumer: {e}", exc_info=True
            )
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 DeliberationsCompleteProgressConsumer: polling started")

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
        - Extract ceremony_id, story_id
        - Update ceremony progress (mark story deliberations as complete)
        - ACK/NAK
        """
        ceremony_id = None
        story_id = None

        try:
            # 1. Parse JSON payload (DTO - external format)
            payload = json.loads(msg.data.decode())
            ceremony_id_str = payload.get("ceremony_id", "")
            story_id_str = payload.get("story_id", "")

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
                f"ceremony={ceremony_id.value}, story={story_id.value}"
            )

            # 2. Get ceremony
            ceremony = await self._storage.get_backlog_review_ceremony(ceremony_id)
            if not ceremony:
                logger.warning(
                    f"Ceremony not found: {ceremony_id.value}. "
                    f"Deliberations complete event will be ignored."
                )
                await msg.ack()  # ACK - don't retry if ceremony doesn't exist
                return

            # 3. Update ceremony progress (mark story deliberations as complete)
            # For now, we'll just log it. The ceremony entity can be extended
            # to track which stories have completed deliberations if needed.
            logger.info(
                f"✅ Deliberations complete for story {story_id.value} "
                f"in ceremony {ceremony_id.value}"
            )

            # 4. ACK message (success)
            await msg.ack()

        except ValueError as e:
            # Domain validation error
            logger.error(f"Validation error: {e}", exc_info=True)
            await msg.ack()  # ACK - don't retry validation errors

        except Exception as e:
            # Unexpected error - retry
            logger.error(
                f"Error handling deliberations complete event for ceremony {ceremony_id.value if ceremony_id else 'unknown'}, "
                f"story {story_id.value if story_id else 'unknown'}: {e}",
                exc_info=True
            )
            await msg.nak()

    async def stop(self) -> None:
        """Stop consumer and cleanup."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("DeliberationsCompleteProgressConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("DeliberationsCompleteProgressConsumer stopped")
