"""Consumer for agent.response.completed events (task extraction results).

Inbound Adapter (Infrastructure):
- Listens to agent.response.completed NATS events
- Filters task extraction results (task_type: "TASK_EXTRACTION" in metadata)
- Parses NATS message payload (JSON with tasks array)
- Creates tasks in Planning Service with associated agent deliberations
"""

import asyncio
import json
import logging

from backlog_review_processor.application.ports.messaging_port import MessagingPort
from backlog_review_processor.application.ports.planning_port import (
    PlanningPort,
    TaskCreationRequest,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_durable import NATSDurable
from backlog_review_processor.domain.value_objects.nats_stream import NATSStream
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject

logger = logging.getLogger(__name__)


class TaskExtractionResultConsumer:
    """Consumer for task extraction results from Ray Executor.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to agent.response.completed (NATS)
    - Filters task extraction results (task_type: "TASK_EXTRACTION")
    - Parses NATS payload (JSON with tasks array)
    - Creates tasks in Planning Service via PlanningPort

    Responsibilities (ONLY):
    - NATS subscription management
    - Message polling
    - Filtering (task_type: "TASK_EXTRACTION")
    - DTO parsing (NATS → domain VOs)
    - Task creation via PlanningPort
    - ACK/NAK handling
    """

    def __init__(
        self,
        nats_client,
        jetstream,
        planning: PlanningPort,
        messaging: MessagingPort,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            planning: Planning port for creating tasks
            messaging: Messaging port for publishing events
        """
        self._nc = nats_client
        self._js = jetstream
        self._planning = planning
        self._messaging = messaging
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming agent.response.completed.task-extraction events."""
        try:
            # Create PULL subscription (durable)
            # Listen to agent.response.completed.task-extraction (specific subject for task extraction)
            # Filter at NATS level using specific subject (no need for payload filtering)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.AGENT_RESPONSE_COMPLETED_TASK_EXTRACTION),
                durable="backlog-review-processor-task-extraction-v2",  # Changed name to create new consumer
                stream=str(NATSStream.AGENT_RESPONSES),
            )

            logger.info("✓ TaskExtractionResultConsumer: subscription created (DURABLE)")

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start TaskExtractionResultConsumer: {e}", exc_info=True
            )
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 TaskExtractionResultConsumer: polling started")

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
        """Handle agent.response.completed message for task extraction.

        Responsibilities:
        - Parse NATS message (DTO)
        - Filter task extraction results (task_type: "TASK_EXTRACTION")
        - Parse JSON response with tasks array
        - Create tasks in Planning Service
        - ACK/NAK
        """
        try:
            # 1. Parse JSON payload → Generated DTO (from AsyncAPI)
            from core.nats.infrastructure.mappers.agent_response_mapper import (
                AgentResponseMapper,
            )

            agent_response = AgentResponseMapper.from_nats_bytes(msg.data)

            # 2. Extract metadata from generated DTO
            if not agent_response.constraints or not agent_response.constraints.metadata:
                logger.error(
                    f"Missing constraints or metadata in AgentResponsePayload for {agent_response.task_id}"
                )
                await msg.nak()
                return

            metadata = agent_response.constraints.metadata
            story_id_str = metadata.story_id or ""
            ceremony_id_str = metadata.ceremony_id or ""

            if not story_id_str or not ceremony_id_str:
                logger.error(
                    f"Missing story_id or ceremony_id in metadata for {agent_response.task_id}"
                )
                await msg.nak()
                return

            story_id = StoryId(story_id_str)
            ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)

            logger.info(
                f"📥 Received task extraction result: {agent_response.task_id} "
                f"(story: {story_id_str}, ceremony: {ceremony_id_str})"
            )

            # 3. Extract proposal/response from agent (using generated DTO)
            proposal_data = agent_response.proposal
            if isinstance(proposal_data, dict):
                llm_response = proposal_data.get("content", str(proposal_data))
            elif isinstance(proposal_data, str):
                llm_response = proposal_data
            else:
                llm_response = str(proposal_data) if proposal_data else ""

            # 4. Parse JSON response (expects {"tasks": [...]})
            try:
                response_json = json.loads(llm_response)
                tasks_data = response_json.get("tasks", [])
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in task extraction response for {agent_response.task_id}: {e}"
                )
                await msg.nak()
                return

            if not tasks_data:
                logger.warning(f"No tasks found in extraction response for {agent_response.task_id}")
                await msg.ack()  # ACK - no tasks to create
                return

            # 5. Create tasks in Planning Service
            created_count = 0
            for i, task_data in enumerate(tasks_data):
                try:
                    # Extract task fields
                    task_title = task_data.get("title", "")
                    task_description = task_data.get("description", "")
                    estimated_hours = task_data.get("estimated_hours", 0)
                    deliberation_indices = task_data.get("deliberation_indices", [])

                    if not task_title:
                        logger.warning(
                            f"Skipping task {i} in extraction result: missing title"
                        )
                        continue

                    # Create task in Planning Service
                    request = TaskCreationRequest(
                        story_id=story_id,
                        title=task_title,
                        description=task_description,
                        estimated_hours=estimated_hours,
                        deliberation_indices=deliberation_indices,
                        ceremony_id=ceremony_id,
                    )

                    created_task_id = await self._planning.create_task(request)

                    created_count += 1
                    logger.info(
                        f"✅ Created task {created_task_id}: {task_title} "
                        f"(associated with {len(deliberation_indices)} deliberations)"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to create task {i} from extraction result for {agent_response.task_id}: {e}",
                        exc_info=True,
                    )
                    # Continue with next task
                    continue

            # 6. ACK message (success)
            await msg.ack()

            logger.info(
                f"✅ Task extraction completed: created {created_count}/{len(tasks_data)} tasks "
                f"for story {story_id_str}"
            )

        except ValueError as e:
            # Domain validation error
            logger.error(f"Validation error: {e}", exc_info=True)
            await msg.ack()  # ACK - don't retry validation errors

        except Exception as e:
            # Unexpected error - retry
            logger.error(f"Error handling extraction result: {e}", exc_info=True)
            await msg.nak()

    async def stop(self) -> None:
        """Stop consumer and cleanup."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("TaskExtractionResultConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("TaskExtractionResultConsumer stopped")

    async def _publish_tasks_complete_event(
        self,
        ceremony_id,
        story_id,
        tasks_created: int,
    ) -> None:
        """Publish tasks.complete event for Planning Service to track progress.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            tasks_created: Number of tasks created
        """
        from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject

        payload = {
            "ceremony_id": ceremony_id.value,
            "story_id": story_id.value,
            "tasks_created": tasks_created,
        }

        await self._messaging.publish_event(
            subject=str(NATSSubject.TASKS_COMPLETE),
            payload=payload,
        )

        logger.info(
            f"✅ Published tasks complete event for story {story_id.value} "
            f"in ceremony {ceremony_id.value} ({tasks_created} tasks created)"
        )

