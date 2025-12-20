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
from typing import Any

from backlog_review_processor.application.ports.messaging_port import MessagingPort
from backlog_review_processor.application.ports.planning_port import (
    PlanningPort,
    TaskCreationRequest,
)
from backlog_review_processor.domain.entities.extracted_task import ExtractedTask
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_durable import NATSDurable
from backlog_review_processor.domain.value_objects.nats_stream import NATSStream
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from backlog_review_processor.infrastructure.mappers.agent_response_mapper import (
    AgentResponseMapper,
)

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
        max_deliveries: int = 3,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            planning: Planning port for creating tasks
            messaging: Messaging port for publishing events
            max_deliveries: Maximum number of delivery attempts before DLQ
        """
        self._nc = nats_client
        self._js = jetstream
        self._planning = planning
        self._messaging = messaging
        self._max_deliveries = max_deliveries
        self._subscription = None
        self._polling_task = None
        self._processed_task_ids: set[str] = set()  # Idempotency tracking

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

    def _extract_metadata(
        self, agent_response: Any
    ) -> tuple[StoryId, BacklogReviewCeremonyId] | None:
        """Extract story_id and ceremony_id from agent response metadata.

        Args:
            agent_response: AgentResponsePayload DTO

        Returns:
            Tuple of (story_id, ceremony_id) or None if invalid
        """
        if not agent_response.constraints or not agent_response.constraints.metadata:
            logger.error(
                f"Missing constraints or metadata in AgentResponsePayload for {agent_response.task_id}"
            )
            return None

        metadata = agent_response.constraints.metadata
        story_id_str = metadata.story_id or ""
        ceremony_id_str = metadata.ceremony_id or ""

        if not story_id_str or not ceremony_id_str:
            logger.error(
                f"Missing story_id or ceremony_id in metadata for {agent_response.task_id}"
            )
            return None

        return StoryId(story_id_str), BacklogReviewCeremonyId(ceremony_id_str)

    def _extract_llm_response(self, proposal_data: Any) -> str:
        """Extract LLM response string from proposal data.

        Args:
            proposal_data: Proposal data (dict, str, or other)

        Returns:
            LLM response as string
        """
        if isinstance(proposal_data, dict):
            return proposal_data.get("content", str(proposal_data))
        elif isinstance(proposal_data, str):
            return proposal_data
        else:
            return str(proposal_data) if proposal_data else ""

    def _parse_tasks_json(self, llm_response: str, task_id: str) -> list[dict[str, Any]] | None:
        """Parse JSON response and extract tasks array.

        Args:
            llm_response: LLM response string (JSON)
            task_id: Task ID for error logging

        Returns:
            List of task dictionaries or None if invalid
        """
        try:
            response_json = json.loads(llm_response)
            tasks_data = response_json.get("tasks", [])
            return tasks_data
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in task extraction response for {task_id}: {e}"
            )
            return None

    def _create_extracted_task(
        self,
        task_data: dict[str, Any],
        story_id: StoryId,
        ceremony_id: BacklogReviewCeremonyId,
        task_index: int,
    ) -> ExtractedTask | None:
        """Create ExtractedTask domain entity from task data.

        Args:
            task_data: Task data dictionary from JSON
            story_id: Story identifier
            ceremony_id: Ceremony identifier
            task_index: Index of task in array (for logging)

        Returns:
            ExtractedTask domain entity or None if invalid
        """
        task_title = task_data.get("title", "")
        if not task_title:
            logger.warning(
                f"Skipping task {task_index} in extraction result: missing title"
            )
            return None

        try:
            return ExtractedTask(
                story_id=story_id,
                ceremony_id=ceremony_id,
                title=task_title,
                description=task_data.get("description", ""),
                estimated_hours=task_data.get("estimated_hours", 0),
                deliberation_indices=task_data.get("deliberation_indices", []),
            )
        except ValueError as e:
            logger.error(
                f"Invalid extracted task data at index {task_index}: {e}",
                exc_info=True,
            )
            return None

    async def _create_task_in_planning(
        self, extracted_task: ExtractedTask
    ) -> str | None:
        """Create task in Planning Service from extracted task.

        Args:
            extracted_task: ExtractedTask domain entity

        Returns:
            Created task ID or None if creation failed
        """
        try:
            request = TaskCreationRequest(
                story_id=extracted_task.story_id,
                title=extracted_task.title,
                description=extracted_task.description,
                estimated_hours=extracted_task.estimated_hours,
                deliberation_indices=extracted_task.deliberation_indices,
                ceremony_id=extracted_task.ceremony_id,
            )

            created_task_id = await self._planning.create_task(request)

            logger.info(
                f"✅ Created task {created_task_id}: {extracted_task.title} "
                f"(associated with {len(extracted_task.deliberation_indices)} deliberations)"
            )
            return created_task_id

        except Exception as e:
            logger.error(
                f"Failed to create task '{extracted_task.title}' in Planning Service: {e}",
                exc_info=True,
            )
            return None

    async def _handle_message(self, msg) -> None:
        """Handle agent.response.completed message for task extraction.

        Responsibilities:
        - Parse NATS message (DTO)
        - Detect canonical vs legacy events
        - Parse JSON response with tasks array (or use canonical tasks)
        - Create tasks in Planning Service
        - ACK/NAK with max deliveries check
        - Idempotency by task_id
        """
        # Extract delivery count from NATS message metadata
        try:
            deliveries = msg.metadata.num_delivered
        except AttributeError:
            deliveries = 1
        
        try:
            # Parse JSON payload
            payload = json.loads(msg.data.decode("utf-8"))
            
            # Detect if this is a canonical event (has tasks already parsed)
            if "tasks" in payload and isinstance(payload.get("tasks"), list):
                # Canonical event: tasks already parsed
                await self._handle_canonical_event(payload, msg)
            else:
                # Legacy event: parse proposal
                await self._handle_legacy_event(payload, msg)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            if deliveries >= self._max_deliveries:
                logger.error(f"Max deliveries exceeded, dropping message")
                await msg.ack()  # Drop invalid message
            else:
                await msg.nak()  # Retry
        except Exception as e:
            logger.error(
                f"Error processing task extraction result (delivery {deliveries}): {e}",
                exc_info=True
            )
            if deliveries >= self._max_deliveries:
                logger.error(f"Max deliveries exceeded, dropping message")
                await msg.ack()  # Drop after max retries
            else:
                await msg.nak()  # Retry with backoff
    
    async def _handle_canonical_event(
        self,
        payload: dict[str, Any],
        msg,
    ) -> None:
        """Procesar evento canónico con tasks ya parseados.
        
        Args:
            payload: Event payload with tasks already parsed
            msg: NATS message
        """
        task_id = payload.get("task_id")
        story_id_str = payload.get("story_id")
        ceremony_id_str = payload.get("ceremony_id")
        tasks = payload.get("tasks", [])
        
        if not task_id:
            logger.error("Missing task_id in canonical event")
            await msg.nak()
            return
        
        # Idempotency check
        if task_id in self._processed_task_ids:
            logger.warning(
                f"Duplicate task_id {task_id}, ignoring (idempotency)"
            )
            await msg.ack()
            return
        
        if not story_id_str or not ceremony_id_str:
            logger.error(
                f"Missing story_id or ceremony_id in canonical event: {task_id}"
            )
            await msg.nak()
            return
        
        story_id = StoryId(story_id_str)
        ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
        
        logger.info(
            f"📥 Received canonical task extraction event: {task_id} "
            f"(story: {story_id.value}, ceremony: {ceremony_id.value}, "
            f"tasks: {len(tasks)})"
        )
        
        if not tasks:
            logger.warning(
                f"No tasks found in canonical event for {task_id}"
            )
            await msg.ack()
            return
        
        # Create tasks in Planning Service
        created_count = 0
        for i, task_data in enumerate(tasks):
            extracted_task = self._create_extracted_task(
                task_data, story_id, ceremony_id, i
            )
            if not extracted_task:
                continue
            
            task_id_created = await self._create_task_in_planning(extracted_task)
            if task_id_created:
                created_count += 1
        
        # Mark as processed (idempotency)
        self._processed_task_ids.add(task_id)
        
        # ACK message (success)
        await msg.ack()
        
        logger.info(
            f"✅ Created {created_count} tasks from canonical event: {task_id}"
        )
    
    async def _handle_legacy_event(
        self,
        payload: dict[str, Any],
        msg,
    ) -> None:
        """Procesar evento legacy (backward compatibility).
        
        Args:
            payload: Legacy event payload
            msg: NATS message
        """
        try:
            # Parse JSON payload → Generated DTO
            agent_response = AgentResponseMapper.from_nats_json(payload)
            
            # Idempotency check
            if agent_response.task_id in self._processed_task_ids:
                logger.warning(
                    f"Duplicate task_id {agent_response.task_id}, ignoring (idempotency)"
                )
                await msg.ack()
                return
            
            # Extract metadata
            metadata_result = self._extract_metadata(agent_response)
            if not metadata_result:
                await msg.nak()
                return
            
            story_id, ceremony_id = metadata_result
            
            logger.info(
                f"📥 Received legacy task extraction result: {agent_response.task_id} "
                f"(story: {story_id.value}, ceremony: {ceremony_id.value})"
            )
            
            # Extract LLM response
            llm_response = self._extract_llm_response(agent_response.proposal)
            
            # Parse tasks JSON
            tasks_data = self._parse_tasks_json(llm_response, agent_response.task_id)
            if tasks_data is None:
                await msg.nak()
                return
            
            if not tasks_data:
                logger.warning(
                    f"No tasks found in extraction response for {agent_response.task_id}"
                )
                await msg.ack()
                return
            
            # Create tasks in Planning Service
            created_count = 0
            for i, task_data in enumerate(tasks_data):
                extracted_task = self._create_extracted_task(
                    task_data, story_id, ceremony_id, i
                )
                if not extracted_task:
                    continue
                
                task_id = await self._create_task_in_planning(extracted_task)
                if task_id:
                    created_count += 1
            
            # Mark as processed (idempotency)
            self._processed_task_ids.add(agent_response.task_id)
            
            # ACK message (success)
            await msg.ack()
            
            logger.info(
                f"✅ Task extraction completed: created {created_count}/{len(tasks_data)} tasks "
                f"for story {story_id.value}"
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

