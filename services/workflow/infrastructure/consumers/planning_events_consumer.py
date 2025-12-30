"""Planning events consumer.

Consumes planning.story.transitioned events and initializes workflow states.
Following Hexagonal Architecture.
"""

import asyncio
import json
import logging

from core.shared.events.infrastructure import parse_required_envelope
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from services.workflow.application.contracts.planning_service_contract import (
    PlanningStoryState,
)
from services.workflow.application.dto.planning_event_dto import (
    PlanningStoryTransitionedDTO,
)
from services.workflow.application.usecases.initialize_task_workflow_usecase import (
    InitializeTaskWorkflowUseCase,
)
from services.workflow.domain.value_objects.nats_subjects import NatsSubjects
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.infrastructure.mappers.planning_event_mapper import (
    PlanningEventMapper,
)

logger = logging.getLogger(__name__)


class PlanningEventsConsumer:
    """NATS consumer for planning.story.transitioned events.

    Listens to story transitions and initializes workflow states for tasks.
    Uses PULL subscription (supports multiple replicas).

    Event schema:
    {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": ["task-001", "task-002", "task-003"],
        "timestamp": "2025-11-06T10:30:00Z"
    }

    Following Hexagonal Architecture:
    - Infrastructure layer (NATS-specific concerns only)
    - Uses mapper to deserialize (NATS message → DTO)
    - Calls use case for business logic (DTO → domain → persist)
    - Clean separation: consumer (infra) → mapper (infra) → use case (app) → domain
    """

    def __init__(
        self,
        nats_client: NATS,
        jetstream: JetStreamContext,
        initialize_task_workflow: InitializeTaskWorkflowUseCase,
    ) -> None:
        """Initialize consumer.

        Following Hexagonal Architecture:
        - Consumer depends on use case (not repository/messaging directly)
        - Use case orchestrates business logic
        - Consumer only handles NATS-specific concerns

        Args:
            nats_client: NATS client
            jetstream: JetStream context
            initialize_task_workflow: Use case for task workflow initialization
        """
        self._nats = nats_client
        self._js = jetstream
        self._initialize_task_workflow = initialize_task_workflow
        self._subscription = None
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start consuming planning.story.transitioned events.

        Uses PULL subscription:
        - Durable: workflow-planning-events-v1
        - Stream: PLANNING_EVENTS
        - Subject: planning.story.transitioned
        - Multiple replicas supported (queue-group-like behavior)
        """
        logger.info("Starting PlanningEventsConsumer (PULL subscription)...")

        # PULL subscription (supports multiple replicas)
        self._subscription = await self._js.pull_subscribe(
            subject=str(NatsSubjects.PLANNING_STORY_TRANSITIONED),
            durable="workflow-planning-events-v1",
            stream="PLANNING_EVENTS",
        )

        # Start background polling task
        task = asyncio.create_task(self._poll_messages())
        self._tasks.append(task)

        logger.info("✅ PlanningEventsConsumer started (PULL mode)")

    async def stop(self) -> None:
        """Stop consumer gracefully."""
        logger.info("Stopping PlanningEventsConsumer...")

        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("✅ PlanningEventsConsumer stopped")

    async def _poll_messages(self):  # pragma: no cover
        """Poll for messages (infinite background loop).

        Marked as no cover: Infinite loop for production.
        Business logic in _handle_message() is unit tested.
        """
        try:
            while True:
                try:
                    # Fetch 10 messages, wait max 5 seconds
                    messages = await self._subscription.fetch(batch=10, timeout=5)

                    for msg in messages:
                        await self._handle_message(msg)
                        await msg.ack()

                except TimeoutError:
                    # No messages available, continue polling
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error polling messages: {e}", exc_info=True)
                    await asyncio.sleep(1)  # Backoff on error

        except asyncio.CancelledError:
            logger.info("_poll_messages task cancelled, shutting down...")
            raise

    async def _handle_message(self, msg) -> None:
        """Handle planning.story.transitioned message.

        Uses mapper to deserialize event and initializes workflow states for tasks.
        This method contains business logic and IS unit tested.

        Following Hexagonal Architecture:
        - Mapper deserializes NATS message → DTO
        - Consumer converts DTO → domain objects
        - Use cases execute business logic

        Args:
            msg: NATS message
        """
        try:
            # Parse and require EventEnvelope (no legacy fallback)
            data = json.loads(msg.data.decode("utf-8"))
            envelope = parse_required_envelope(data)
            payload = envelope.payload

            logger.info(
                f"📥 [EventEnvelope] Received planning.story.transitioned. "
                f"correlation_id={envelope.correlation_id}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            # Deserialize via mapper (payload only)
            event_dto: PlanningStoryTransitionedDTO = PlanningEventMapper.from_payload(payload)

            # Only process if story is READY_FOR_EXECUTION
            if event_dto.to_state != PlanningStoryState.READY_FOR_EXECUTION:
                logger.debug(
                    f"Ignoring story {event_dto.story_id} transition to {event_dto.to_state} "
                    f"(not {PlanningStoryState.READY_FOR_EXECUTION})"
                )
                return

            # Convert DTO → domain objects
            story_id = StoryId(event_dto.story_id)
            task_ids = [TaskId(tid) for tid in event_dto.tasks]

            logger.info(
                f"📋 Initializing workflow for story {story_id} "
                f"with {len(task_ids)} tasks"
            )

            # Initialize workflow state for each task (via use case)
            for task_id in task_ids:
                await self._initialize_task_workflow.execute(
                    task_id=task_id,
                    story_id=story_id,
                )

            logger.info(
                f"✅ Workflow initialized for story {story_id} "
                f"({len(task_ids)} tasks). "
                f"correlation_id={envelope.correlation_id}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..."
            )

        except KeyError as e:
            logger.error(f"Missing required field in event: {e}", exc_info=True)
            # Don't ack message with missing fields (will retry)
            raise

        except ValueError as e:
            logger.error(f"Invalid data in event: {e}", exc_info=True)
            # Invalid data = business error, log and continue (ack message)
            # Don't retry invalid data forever

        except Exception as e:
            logger.error(f"Error handling planning event: {e}", exc_info=True)
            # Unexpected error, don't ack (will retry)
            raise

