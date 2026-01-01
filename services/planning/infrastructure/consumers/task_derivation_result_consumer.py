"""Consumer for agent.response.completed events (task derivation results).

Inbound Adapter (Infrastructure):
- Listens to agent.response.completed NATS events
- Filters task derivation results (task_id starts with "derive-")
- Parses NATS message payload
- Delegates to ProcessTaskDerivationResultUseCase
"""

import asyncio
import json
import logging

from core.shared.events.infrastructure import parse_required_envelope
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.domain.value_objects.nats_durable import NATSDurable
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)
from planning.infrastructure.mappers.task_derivation_result_payload_mapper import (
    TaskDerivationResultPayloadMapper,
)

logger = logging.getLogger(__name__)


class TaskDerivationResultConsumer:
    """Consumer for task derivation results from Ray Executor.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to agent.response.completed (NATS)
    - Filters task derivation results
    - Parses NATS payload
    - Delegates to ProcessTaskDerivationResultUseCase

    Responsibilities (ONLY):
    - NATS subscription management
    - Message polling
    - Filtering (derive-* task_ids)
    - DTO parsing (NATS → domain VOs via mapper)
    - ACK/NAK handling
    - Delegation to use case

    NOT responsible for:
    - Business logic (use case)
    - Task persistence (use case)
    - Event publishing (use case)
    - Dependency validation (domain)
    """

    def __init__(
        self,
        nats_client,
        jetstream,
        task_derivation_service: TaskDerivationResultService,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            task_derivation_service: Application service for processing derivation results
        """
        self._nc = nats_client
        self._js = jetstream
        self._task_derivation = task_derivation_service
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming agent.response.completed events."""
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.AGENT_RESPONSE_COMPLETED),
                durable=str(NATSDurable.TASK_DERIVATION_RESULT),
                stream=str(NATSStream.AGENT_RESPONSES),
            )

            logger.info("✓ TaskDerivationResultConsumer: subscription created (DURABLE)")

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(f"Failed to start TaskDerivationResultConsumer: {e}", exc_info=True)
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 TaskDerivationResultConsumer: polling started")

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
        """Handle agent.response.completed message.

        Responsibilities:
        - Parse NATS message (DTO)
        - Extract envelope if present (for logging)
        - Filter derive-* tasks
        - Map LLM text → TaskNode VOs (via mapper)
        - Delegate to use case
        - ACK/NAK
        """
        try:
            # 1. Parse JSON payload (DTO - external format)
            data = json.loads(msg.data.decode())

            # Require EventEnvelope (no legacy fallback)
            envelope = parse_required_envelope(data)
            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            payload = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received agent response: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            task_id = payload.get("task_id", "")

            # 2. Filter: only task derivation results
            if not task_id.startswith("derive-"):
                # Not a task derivation - ignore and ACK
                await msg.ack()
                return

            logger.info(
                f"📥 Received task derivation result: {task_id}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # 3. Extract domain VOs from payload (DTO → VO via mapper)
            try:
                plan_id = TaskDerivationResultPayloadMapper.extract_plan_id(
                    payload, task_id
                )
                story_id = TaskDerivationResultPayloadMapper.extract_story_id(payload)
                role_str = TaskDerivationResultPayloadMapper.extract_role(payload)
                generated_text = TaskDerivationResultPayloadMapper.extract_llm_text(
                    payload
                )
            except ValueError as e:
                logger.error(
                    f"Invalid payload for {task_id}: {e}",
                    exc_info=True,
                )
                await msg.nak()
                return

            # 6. Parse tasks (DTO → VOs via mapper - anti-corruption layer)
            task_nodes = LLMTaskDerivationMapper.from_llm_text(generated_text)

            if not task_nodes:
                logger.error(f"No tasks parsed from LLM result for {task_id}")
                await msg.nak()
                return

            logger.info(f"Parsed {len(task_nodes)} tasks for Story {story_id}, delegating to service")

            # 7. Delegate to application service (handles business logic)
            # Task depends on Story, so we pass context from Story (role from event)
            await self._task_derivation.process(
                plan_id=plan_id,
                story_id=story_id,
                role=role_str,
                task_nodes=task_nodes,
            )

            # 7. ACK message (success)
            await msg.ack()

            logger.info(
                f"✅ Task derivation completed for {plan_id}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

        except ValueError as e:
            # Domain validation error (e.g. circular dependencies)
            logger.error(f"Validation error: {e}", exc_info=True)
            await msg.ack()  # ACK - don't retry validation errors

        except Exception as e:
            # Unexpected error - retry
            logger.error(f"Error handling derivation result: {e}", exc_info=True)
            await msg.nak()


    async def stop(self) -> None:
        """Stop consumer and cleanup."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("TaskDerivationResultConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("TaskDerivationResultConsumer stopped")

