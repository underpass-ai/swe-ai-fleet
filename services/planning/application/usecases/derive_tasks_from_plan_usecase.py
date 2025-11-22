"""DeriveTasksFromPlanUseCase - Trigger automatic task derivation via NATS event.

Use Case (Application Layer):
- Orchestrates domain logic
- Depends on ports (interfaces)
- NO infrastructure dependencies
- Event-driven (fire-and-forget)
- Publishes task.derivation.requested event for Task Derivation Service
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId

logger = logging.getLogger(__name__)


@dataclass
class DeriveTasksFromPlanUseCase:
    """Use case for triggering automatic task derivation.

    Flow (Event-Driven):
    1. Fetch plan from storage to validate it exists
    2. Publish task.derivation.requested event to NATS
    3. Return deliberation_id immediately (fire-and-forget)
    4. Task Derivation Service (separate microservice) consumes the event
    5. Planning Service listens for task.derivation.completed/failed events

    Following Hexagonal Architecture:
    - Depends ONLY on ports (StoragePort, MessagingPort)
    - Infrastructure adapters injected via constructor
    - NO direct infrastructure calls
    - Uses ONLY Value Objects (NO primitives)

    Responsibilities:
    - Validate plan exists
    - Publish event to trigger derivation
    - Return immediately (non-blocking)
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(self, plan_id: PlanId) -> DeliberationId:
        """Execute task derivation request (fire-and-forget).

        Args:
            plan_id: Plan to derive tasks from

        Returns:
            DeliberationId for tracking the async job

        Raises:
            ValueError: If plan not found or invalid
        """
        logger.info(f"🚀 Triggering task derivation for plan: {plan_id}")

        # Step 1: Fetch plan from storage to validate it exists
        plan = await self.storage.get_plan(plan_id)

        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        logger.debug(f"Validated plan exists: {plan_id}, story_id={plan.story_id}")

        # Step 2: Generate deliberation_id for tracking
        deliberation_id = DeliberationId(f"derive-{uuid4()}")

        # Step 3: Publish task.derivation.requested event
        # Task Derivation Service (separate microservice) will consume this
        payload = {
            "event_type": "task.derivation.requested",
            "deliberation_id": deliberation_id.value,
            "plan_id": plan_id.value,
            "story_id": plan.story_id.value,
            "roles": plan.roles,  # Roles for context rehydration
            "requested_by": "planning-service",
            "requested_at": datetime.now(UTC).isoformat(),
        }

        try:
            await self.messaging.publish_event(
                topic="task.derivation.requested",
                payload=payload,
            )

            logger.info(
                f"✅ Published task.derivation.requested event: {deliberation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to publish task derivation event: {e}")
            raise

        # Step 4: Return immediately (event-driven, fire-and-forget)
        # Planning Service will listen for task.derivation.completed/failed events
        return deliberation_id

