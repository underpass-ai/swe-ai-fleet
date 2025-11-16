"""Consumer for planning.task.created events."""

import asyncio
import json
import logging

from core.context.application.usecases.synchronize_task_from_planning import (
    SynchronizeTaskFromPlanningUseCase,
)
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper

from services.context.consumers.planning.base_consumer import BasePlanningConsumer

logger = logging.getLogger(__name__)


class TaskCreatedConsumer(BasePlanningConsumer):
    """Inbound Adapter for planning.task.created events (ACL)."""

    def __init__(self, js, use_case: SynchronizeTaskFromPlanningUseCase):
        super().__init__(js=js, graph_command=None, cache_service=None)
        self._use_case = use_case

    async def start(self) -> None:
        self._subscription = await self.js.pull_subscribe(
            subject="planning.task.created",
            durable="context-planning-task-created",
            stream="PLANNING_EVENTS",
        )
        logger.info("✓ TaskCreatedConsumer: subscription created (DURABLE)")

        self._polling_task = asyncio.create_task(
            self._poll_messages(self._subscription, self._handle_message)
        )

    async def _handle_message(self, msg) -> None:
        """Orchestration: JSON → DTO → Entity → UseCase."""
        try:
            # 1. Parse JSON payload
            payload = json.loads(msg.data.decode())

            # 2. JSON → Entity (via unified mapper - ACL)
            task = PlanningEventMapper.payload_to_task(payload)

            # 3. Call use case
            await self._use_case.execute(task)

            # 4. ACK
            await msg.ack()

        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid event data: {e}", exc_info=True)
            await msg.nak()
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            await msg.nak()
