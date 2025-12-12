"""BacklogReviewResultConsumer - Async consumer for story review results.

Infrastructure Layer (Consumer):
- Subscribes to: agent.response.completed (published directly by vLLM/Ray Workers)
- Processes individual agent responses for backlog review
- Calls Planning Service to update ceremony with agent deliberation
- Thin adapter layer (no business logic)

Following Event-Driven Architecture:
- NATS JetStream durable pull subscription
- vLLM publishes agent.response.completed directly
- Task Extraction processes and updates Planning Service via gRPC
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from nats.aio.client import Client
from nats.js import JetStreamContext
from backlog_review_processor.application.usecases.accumulate_deliberations_usecase import (
    AccumulateDeliberationsUseCase,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_durable import NATSDurable
from backlog_review_processor.domain.value_objects.nats_stream import NATSStream
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)

logger = logging.getLogger(__name__)


@dataclass
class BacklogReviewResultConsumer:
    """
    NATS consumer for backlog review story review results.

    Responsibilities:
    - Subscribe to agent.response.completed events (published by Ray Workers)
    - Process individual agent responses
    - Accumulate deliberations in-memory
    - Thin adapter layer (no business logic)

    Following Hexagonal Architecture:
    - Uses AccumulateDeliberationsUseCase (application layer)
    - Consumer is pure infrastructure (message handling only)
    - Domain-driven design with ValueObjects
    """

    nats_client: Client
    jetstream: JetStreamContext
    accumulate_deliberations: AccumulateDeliberationsUseCase

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
            # Listen to agent.response.completed.backlog-review.role (specific subject for role deliberations)
            # Each agent publishes its own response, Task Extraction processes them individually
            # Use AGENT_RESPONSES stream (where agent.* events are published)
            # Filter at NATS level using specific subject (no need for payload filtering)
            self._subscription = await self.jetstream.pull_subscribe(
                subject=str(NATSSubject.AGENT_RESPONSE_COMPLETED_BACKLOG_REVIEW_ROLE),
                durable="backlog-review-processor-backlog-review-role-v2",  # Changed name to create new consumer
                stream=str(NATSStream.AGENT_RESPONSES),
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
                logger.debug("🔍 [BacklogReviewResultConsumer] Fetching messages from subscription...")
                msgs = await self._subscription.fetch(batch=1, timeout=5)

                if msgs:
                    logger.info(f"📥 [BacklogReviewResultConsumer] Received {len(msgs)} message(s)")
                else:
                    logger.debug("⏳ [BacklogReviewResultConsumer] No messages available (timeout)")

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
        Handle agent.response.completed event (published directly by vLLM/Ray Workers).

        Event payload (from vLLM after completing agent deliberation):
        {
            "task_id": "ceremony-abc:story-ST-123:role-ARCHITECT",
            "agent_id": "agent-architect-001",
            "role": "ARCHITECT",
            "proposal": {...},
            "duration_ms": 45000,
            "timestamp": "2025-12-02T10:30:00Z",
            "num_agents": 3
        }

        Note: Each agent publishes its own response. Task Extraction processes them individually
        and accumulates them in-memory. When all role deliberations are complete, it publishes
        an event to trigger task extraction.
        """
        ceremony_id = None
        story_id = None

        try:
            logger.info(
                f"📥 [BacklogReviewResultConsumer._handle_message] Received message: "
                f"subject={msg.subject if hasattr(msg, 'subject') else 'N/A'}, "
                f"data_size={len(msg.data)} bytes"
            )

            # Parse JSON payload → Generated DTO (from AsyncAPI)
            from backlog_review_processor.infrastructure.mappers.agent_response_mapper import (
                AgentResponseMapper,
            )

            agent_response = AgentResponseMapper.from_nats_bytes(msg.data)

            # Extract metadata from task_id
            # Format: "ceremony-abc123:story-ST-456:role-ARCHITECT"
            task_id = agent_response.task_id
            logger.info(
                f"🔍 [BacklogReviewResultConsumer._handle_message] Parsed message: "
                f"task_id={task_id}, "
                f"agent_id={agent_response.agent_id}, "
                f"role={agent_response.role}, "
                f"has_constraints={agent_response.constraints is not None}"
            )
            if not task_id:
                logger.warning("⚠️ [BacklogReviewResultConsumer] Missing task_id in agent.response.completed event")
                await msg.ack()
                return

            # Parse task_id (format: "ceremony-{id}:story-{id}:role-{role}")
            # Note: Since we're subscribed to agent.response.completed.backlog-review.role,
            # NATS already filters events for us. We only need to validate the format.
            if not task_id.startswith("ceremony-"):
                logger.warning(f"Unexpected task_id format (expected ceremony-*): {task_id}")
                await msg.ack()
                return

            parts = task_id.split(":")
            if len(parts) != 3:
                logger.error(f"Invalid task_id format (expected 3 parts): {task_id}")
                await msg.nak()
                return

            if not (parts[0].startswith("ceremony-") and
                    parts[1].startswith("story-") and
                    parts[2].startswith("role-")):
                logger.error(f"Invalid task_id format (expected ceremony-*:story-*:role-*): {task_id}")
                await msg.nak()
                return

            ceremony_id_str = parts[0].replace("ceremony-", "")
            story_id_str = parts[1].replace("story-", "")
            role_str = parts[2].replace("role-", "")

            ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
            story_id = StoryId(story_id_str)

            try:
                role = BacklogReviewRole(role_str)
            except ValueError:
                logger.error(f"Invalid role in task_id: {role_str}")
                await msg.nak()
                return

            # Extract proposal content (using generated DTO)
            proposal_data = agent_response.proposal

            # Extract timestamp (using generated DTO)
            timestamp_str = agent_response.timestamp
            if timestamp_str:
                try:
                    reviewed_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except Exception:
                    reviewed_at = datetime.now(UTC)
            else:
                reviewed_at = datetime.now(UTC)

            logger.info(
                f"📥 Received agent.response.completed for backlog review: "
                f"ceremony={ceremony_id.value}, story={story_id.value}, "
                f"role={role.value}, agent={agent_response.agent_id or 'unknown'}"
            )

            # Accumulate deliberation (in-memory, detects completion)
            await self.accumulate_deliberations.execute(
                ceremony_id=ceremony_id,
                story_id=story_id,
                agent_id=agent_response.agent_id or "unknown",
                role=role,
                proposal=proposal_data or {},
                reviewed_at=reviewed_at,
            )

            # ACK message after processing
            await msg.ack()

            logger.info(
                f"✓ Processed agent response: ceremony={ceremony_id.value}, "
                f"story={story_id.value}, role={role.value}, agent={agent_response.agent_id or 'unknown'}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process backlog review agent.response.completed event for ceremony {ceremony_id.value if ceremony_id else 'unknown'}, "
                f"story {story_id.value if story_id else 'unknown'}: {e}",
                exc_info=True
            )
            await msg.nak()  # NACK = will retry
