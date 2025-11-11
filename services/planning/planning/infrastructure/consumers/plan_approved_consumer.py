"""Consumer for planning.plan.approved events.

Inbound Adapter (Infrastructure):
- Listens to planning.plan.approved NATS events
- Triggers automatic task derivation
- Event-driven architecture
"""

import asyncio
import json
import logging

from planning.application.usecases.derive_tasks_from_plan_usecase import (
    DeriveTasksFromPlanUseCase,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.nats_durable import NATSDurable
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject

logger = logging.getLogger(__name__)


class PlanApprovedConsumer:
    """Consumer for planning.plan.approved events.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to external events (NATS)
    - Converts DTO → VO via mapper (anti-corruption layer)
    - Delegates to use case (application layer)

    Responsibilities:
    - Subscribe to planning.plan.approved
    - Parse NATS message payload
    - Extract plan_id and convert to VO
    - Call DeriveTasksFromPlanUseCase
    - Handle errors and ACK/NAK
    """

    def __init__(
        self,
        nats_client,
        jetstream,
        derive_tasks_usecase: DeriveTasksFromPlanUseCase,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            derive_tasks_usecase: Use case for task derivation
        """
        self._nc = nats_client
        self._js = jetstream
        self._derive_tasks = derive_tasks_usecase
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming planning.plan.approved events.

        Uses PULL subscription for reliability and load balancing.
        """
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.PLAN_APPROVED),
                durable=str(NATSDurable.PLAN_APPROVED_TASK_DERIVATION),
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info("✓ PlanApprovedConsumer: subscription created (DURABLE)")

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(f"Failed to start PlanApprovedConsumer: {e}", exc_info=True)
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 PlanApprovedConsumer: polling started")

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
        """Handle individual planning.plan.approved message.

        Args:
            msg: NATS message
        """
        try:
            # 1. Parse JSON payload (DTO - external format)
            payload = json.loads(msg.data.decode())

            logger.info(f"📥 Received plan approval: {payload.get('plan_id')}")

            # 2. Convert DTO → VO (anti-corruption layer)
            # Mapper is simple here - just extract plan_id
            plan_id = PlanId(payload["plan_id"])

            # 3. Call use case (application layer)
            deliberation_id = await self._derive_tasks.execute(plan_id)

            logger.info(
                f"✅ Task derivation submitted: {deliberation_id} for plan {plan_id}"
            )

            # 4. ACK message (success)
            await msg.ack()

        except KeyError as e:
            # Missing required field in payload
            logger.warning(f"Invalid event payload (missing {e})", exc_info=True)
            await msg.nak()  # Retry

        except ValueError as e:
            # Domain validation error
            logger.error(f"Domain validation error: {e}", exc_info=True)
            await msg.nak()  # Retry

        except Exception as e:
            # Unexpected error
            logger.error(f"Error processing plan approval: {e}", exc_info=True)
            await msg.nak()  # Retry

    async def stop(self) -> None:
        """Stop consumer and cleanup resources."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        logger.info("PlanApprovedConsumer stopped")

