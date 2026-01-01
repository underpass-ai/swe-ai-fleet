"""Consumer for planning.backlog_review.tasks.complete events.

Inbound Adapter (Infrastructure):
- Listens to planning.backlog_review.tasks.complete NATS events
- Published by Task Extraction Service when all tasks for a story have been created
- Updates ceremony progress in Planning Service
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from core.shared.events.infrastructure import parse_required_envelope
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


class TasksCompleteProgressConsumer:
    """Consumer for tasks complete events to track progress.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to planning.backlog_review.tasks.complete (NATS)
    - Updates ceremony progress in storage

    Responsibilities (ONLY):
    - NATS subscription management
    - Message polling
    - DTO parsing (NATS → domain VOs)
    - Update ceremony progress (mark story tasks as complete)
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
        """Start consuming planning.backlog_review.tasks.complete events."""
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.TASKS_COMPLETE),
                durable="planning-tasks-complete-progress",
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info(
                "✓ TasksCompleteProgressConsumer: subscription created (DURABLE)"
            )

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start TasksCompleteProgressConsumer: {e}", exc_info=True
            )
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 TasksCompleteProgressConsumer: polling started")

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
        """Handle planning.backlog_review.tasks.complete message.

        Responsibilities:
        - Parse NATS message (DTO)
        - Extract ceremony_id, story_id, tasks_created
        - Update ceremony progress (mark story tasks as complete)
        - ACK/NAK
        """
        ceremony_id = None
        story_id = None

        try:
            # 1. Parse JSON payload (DTO - external format)
            data = json.loads(msg.data.decode())

            # Require EventEnvelope (no legacy fallback)
            envelope = parse_required_envelope(data)
            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            payload = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received tasks complete event: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            ceremony_id_str = payload.get("ceremony_id", "")
            story_id_str = payload.get("story_id", "")
            tasks_created = payload.get("tasks_created", 0)

            if not ceremony_id_str or not story_id_str:
                logger.error(
                    f"Missing ceremony_id or story_id in payload: {payload}. "
                    f"correlation_id={correlation_id}, "
                    f"idempotency_key={idempotency_key[:16]}..."
                )
                await msg.nak()
                return

            ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
            story_id = StoryId(story_id_str)

            logger.info(
                f"📥 Received tasks complete event: "
                f"ceremony={ceremony_id.value}, story={story_id.value}, "
                f"tasks_created={tasks_created}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # 2. Get ceremony
            ceremony = await self._storage.get_backlog_review_ceremony(ceremony_id)
            if not ceremony:
                logger.warning(
                    f"Ceremony not found: {ceremony_id.value}. "
                    f"Tasks complete event will be ignored."
                )
                await msg.ack()  # ACK - don't retry if ceremony doesn't exist
                return

            # 3. Update ceremony progress (mark story tasks as complete)
            logger.info(
                f"✅ Tasks complete for story {story_id.value} "
                f"in ceremony {ceremony_id.value} ({tasks_created} tasks created)"
            )

            # 4. Check if ceremony should auto-complete
            # Conditions:
            # - Ceremony is in REVIEWING status
            # - All stories have tasks created
            # - All review_results are decided (not PENDING)
            if ceremony.status.is_reviewing():
                # Check if all stories have tasks
                all_stories_have_tasks = True
                for story_id_check in ceremony.story_ids:
                    tasks = await self._storage.list_tasks(
                        story_id=story_id_check,
                        limit=1,
                        offset=0,
                    )
                    if not tasks:
                        all_stories_have_tasks = False
                        break

                # Check if all review_results are decided (not PENDING)
                all_reviews_decided = all(
                    not result.approval_status.is_pending()
                    for result in ceremony.review_results
                )

                if all_stories_have_tasks and all_reviews_decided:
                    # Auto-complete ceremony
                    completed_at = datetime.now(UTC)
                    completed_ceremony = ceremony.complete(completed_at)

                    await self._storage.save_backlog_review_ceremony(completed_ceremony)
                    logger.info(
                        f"✅ Ceremony {ceremony_id.value} → COMPLETED (auto-complete: "
                        f"all tasks created and all reviews decided)"
                    )
                else:
                    logger.info(
                        f"⏳ Ceremony {ceremony_id.value} not ready for auto-complete: "
                        f"all_stories_have_tasks={all_stories_have_tasks}, "
                        f"all_reviews_decided={all_reviews_decided}"
                    )

            # 5. ACK message (success)
            await msg.ack()

        except ValueError as e:
            # Domain validation error
            logger.error(f"Validation error: {e}", exc_info=True)
            await msg.ack()  # ACK - don't retry validation errors

        except Exception as e:
            # Unexpected error - retry
            logger.error(
                f"Error handling tasks complete event for ceremony {ceremony_id.value if ceremony_id else 'unknown'}, "
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
                logger.info("TasksCompleteProgressConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("TasksCompleteProgressConsumer stopped")
