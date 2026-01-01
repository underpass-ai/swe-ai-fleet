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

import json

from backlog_review_processor.application.usecases.accumulate_deliberations_usecase import (
    AccumulateDeliberationsUseCase,
)
from backlog_review_processor.domain.value_objects.nats_stream import NATSStream
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from backlog_review_processor.infrastructure.mappers.backlog_review_result_mapper import (
    BacklogReviewResultMapper,
)
from core.shared.events.infrastructure import parse_required_envelope
from nats.aio.client import Client
from nats.js import JetStreamContext

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
        try:
            logger.info(
                f"📥 [BacklogReviewResultConsumer._handle_message] Received message: "
                f"subject={msg.subject if hasattr(msg, 'subject') else 'N/A'}, "
                f"data_size={len(msg.data)} bytes"
            )

            # Require EventEnvelope (no legacy fallback)
            data = json.loads(msg.data.decode("utf-8"))
            envelope = parse_required_envelope(data)

            logger.info(
                f"📥 [EventEnvelope] Received backlog review agent response. "
                f"correlation_id={envelope.correlation_id}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            # Map NATS payload (envelope.payload) to domain entity using infrastructure mapper
            backlog_review_result = BacklogReviewResultMapper.from_nats_json(envelope.payload)

            logger.info(
                f"📥 Received agent.response.completed for backlog review: "
                f"ceremony={backlog_review_result.ceremony_id.value}, "
                f"story={backlog_review_result.story_id.value}, "
                f"role={backlog_review_result.role.value}, "
                f"agent={backlog_review_result.agent_id}. "
                f"correlation_id={envelope.correlation_id}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..."
            )

            # Accumulate deliberation (in-memory, detects completion)
            await self.accumulate_deliberations.execute(backlog_review_result)

            # ACK message after processing
            await msg.ack()

            logger.info(
                f"✓ Processed agent response: ceremony={backlog_review_result.ceremony_id.value}, "
                f"story={backlog_review_result.story_id.value}, "
                f"role={backlog_review_result.role.value}, "
                f"agent={backlog_review_result.agent_id}"
            )

        except ValueError as e:
            # Invalid data format (task_id format, missing fields, etc.)
            logger.error(
                f"Invalid agent.response.completed event payload: {e}",
                exc_info=True
            )
            await msg.ack()  # ACK to avoid retrying invalid messages
        except Exception as e:
            # Other errors (network, processing, etc.) - retry
            logger.error(
                f"Failed to process backlog review agent.response.completed event: {e}",
                exc_info=True
            )
            await msg.nak()  # NACK = will retry
