"""Consumer for planning.project.created events."""

import asyncio
import json
import logging

from core.context.application.usecases.synchronize_project_from_planning import (
    SynchronizeProjectFromPlanningUseCase,
)
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper

from services.context.consumers.planning.base_consumer import BasePlanningConsumer

logger = logging.getLogger(__name__)


class ProjectCreatedConsumer(BasePlanningConsumer):
    """Inbound Adapter for planning.project.created events.

    Part of the Anti-Corruption Layer (ACL).

    Responsibility (Hexagonal Architecture + DDD):
    1. Receive NATS message (infrastructure concern)
    2. Parse JSON → DTO (infrastructure contract)
    3. Mapper: DTO → Entity (ACL translation)
    4. Call UseCase.execute(entity) (application layer)
    5. ACK/NAK (infrastructure concern)

    NO business logic here. Only infrastructure orchestration.
    """

    def __init__(
        self,
        js,
        use_case: SynchronizeProjectFromPlanningUseCase,
    ):
        """Initialize consumer with use case dependency injection.

        Args:
            js: JetStream context
            use_case: Application layer use case (injected)
        """
        super().__init__(js=js, graph_command=None, cache_service=None)
        self._use_case = use_case

    async def start(self) -> None:
        """Start consuming planning.project.created events."""
        self._subscription = await self.js.pull_subscribe(
            subject="planning.project.created",
            durable="context-planning-project-created",
            stream="PLANNING_EVENTS",
        )
        logger.info("✓ ProjectCreatedConsumer: subscription created (DURABLE)")

        self._polling_task = asyncio.create_task(
            self._poll_messages(self._subscription, self._handle_message)
        )

    async def _handle_message(self, msg) -> None:
        """Handle NATS message.

        Orchestration (following hexagonal layers):
        1. Parse JSON → DTO
        2. DTO → Entity (via mapper)
        3. Call use case
        4. ACK/NAK

        Args:
            msg: NATS message
        """
        try:
            # 1. Parse JSON payload
            payload = json.loads(msg.data.decode())

            # 2. JSON → Entity (via unified mapper - ACL)
            project = PlanningEventMapper.payload_to_project(payload)

            logger.debug(
                f"Received planning.project.created: {project.project_id.to_string()}",
                extra=project.get_log_context(),
            )

            # 3. Call use case (application layer - domain pure)
            await self._use_case.execute(project)

            # 4. ACK (success)
            await msg.ack()

        except (KeyError, ValueError) as e:
            # DTO parsing or domain validation error
            logger.warning(f"Invalid event data: {e}", exc_info=True)
            await msg.nak()

        except Exception as e:
            # Use case or persistence error
            logger.error(f"Error processing event: {e}", exc_info=True)
            await msg.nak()

