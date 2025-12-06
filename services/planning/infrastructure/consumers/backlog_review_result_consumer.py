"""BacklogReviewResultConsumer - Async consumer for story review results.

Infrastructure Layer (Consumer):
- Subscribes to: planning.backlog_review.story.reviewed (from Orchestrator)
- Delegates processing to ProcessStoryReviewResultUseCase
- Thin adapter layer (no business logic)

Following Event-Driven Architecture:
- NATS JetStream durable pull subscription
- Orchestrator publishes story.reviewed after deliberations
- Planning consumes via use case
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime

from nats.aio.client import Client
from nats.js import JetStreamContext
from planning.application.dto import StoryReviewResultDTO
from planning.application.usecases import ProcessStoryReviewResultUseCase
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.infrastructure.mappers.task_id_parser_mapper import TaskIdParserMapper

logger = logging.getLogger(__name__)


@dataclass
class BacklogReviewResultConsumer:
    """
    NATS consumer for backlog review story review results.

    Responsibilities:
    - Subscribe to planning.backlog_review.story.reviewed events
    - Delegate processing to ProcessStoryReviewResultUseCase
    - Thin adapter layer (no business logic)

    Following Hexagonal Architecture:
    - Uses ProcessStoryReviewResultUseCase (application layer)
    - Consumer is pure infrastructure (message handling only)
    - Domain-driven design with ValueObjects
    """

    nats_client: Client
    jetstream: JetStreamContext
    process_review_result: ProcessStoryReviewResultUseCase

    def __post_init__(self) -> None:
        """Initialize consumer state."""
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming review result events.

        Uses PULL subscription for reliability and load balancing.
        """
        try:
            # Create PULL subscription (durable)
            self._subscription = await self.jetstream.pull_subscribe(
                subject=str(NATSSubject.BACKLOG_REVIEW_STORY_REVIEWED),
                durable="planning-backlog-review-results",
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info("✓ BacklogReviewResultConsumer: subscription created (DURABLE)")

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start BacklogReviewResultConsumer: {e}", exc_info=True
            )
            raise

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("✓ BacklogReviewResultConsumer stopped")
                raise  # Re-raise to properly propagate cancellation
        else:
            logger.info("✓ BacklogReviewResultConsumer stopped")

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 BacklogReviewResultConsumer: polling started")

        while True:
            try:
                # Fetch messages (batch=1, timeout=5s)
                msgs = await self._subscription.fetch(batch=1, timeout=5)

                for msg in msgs:
                    await self._handle_message(msg)

            except TimeoutError:
                # No messages available - continue polling
                continue

            except Exception as e:
                logger.error(f"Error polling messages: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error

    async def _handle_message(self, msg) -> None:
        """
        Handle agent.response.completed event.

        Event payload (AgentResult from Ray Workers):
        {
            "task_id": "ceremony-abc:story-ST-123:role-ARCHITECT",
            "agent_id": "ARCHITECT-agent-1",
            "role": "ARCHITECT",
            "proposal": "Technical feedback...",
            "operations": null,
            "duration_ms": 45000,
            "is_success": true,
            "error_message": null,
            "model": "Qwen/Qwen3-0.6B",
            "timestamp": "2025-12-02T10:30:00Z"
        }
        """
        ceremony_id = None
        story_id = None

        try:
            data = json.loads(msg.data.decode())

            # Validate success
            if not data.get("is_success", False):
                logger.warning(f"Skipping failed agent result: {data.get('error_message')}")
                await msg.ack()  # ACK to avoid retrying failed agents
                return

            # Extract metadata from task_id using mapper
            # Format: "ceremony-abc123:story-ST-456:role-ARCHITECT"
            task_id = data["task_id"]
            ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

            if not ceremony_id or not story_id:
                logger.error(f"Invalid task_id format: {task_id}")
                await msg.nak()
                return

            reviewed_at = datetime.fromisoformat(data["timestamp"])

            logger.info(
                f"📥 Received review result: "
                f"ceremony={ceremony_id.value}, story={story_id.value}, role={role.value}"
            )

            # Create DTO
            review_result_dto = StoryReviewResultDTO(
                ceremony_id=ceremony_id,
                story_id=story_id,
                role=role,
                feedback=data["proposal"],
                reviewed_at=reviewed_at,
            )

            # Delegate to use case (application layer handles business logic)
            await self.process_review_result.execute(review_result_dto)

            # ACK message
            await msg.ack()

            logger.info(
                f"✓ Processed review result for ceremony {ceremony_id.value}, "
                f"story {story_id.value}, role {role.value}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process review result for ceremony {ceremony_id.value if ceremony_id else 'unknown'}, "
                f"story {story_id.value if story_id else 'unknown'}: {e}",
                exc_info=True
            )
            await msg.nak()  # NACK = will retry
