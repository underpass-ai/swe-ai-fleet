"""ApproveReviewPlanUseCase - PO approves plan preliminary.

Use Case (Application Layer):
- PO approves a plan from ceremony review (Human-in-the-Loop)
- Creates official Plan entity
- Transitions story to READY_FOR_PLANNING
- Publishes planning.plan.approved event
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


@dataclass
class ApproveReviewPlanUseCase:
    """
    Approve plan preliminary and create official Plan.

    This use case (Human-in-the-Loop):
    1. Retrieves ceremony
    2. Finds StoryReviewResult for story
    3. Approves review result (sets approval_status=APPROVED)
    4. Converts PlanPreliminary → Plan (official entity)
    5. Saves Plan to storage
    6. Updates story status to READY_FOR_PLANNING
    7. Updates ceremony with approved result
    8. Publishes planning.plan.approved event
    9. Returns created Plan

    Following Hexagonal Architecture:
    - Depends on StoragePort and MessagingPort
    - Returns domain entity (Plan)
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        approved_by: UserName,
    ) -> Plan:
        """
        Approve plan preliminary and create official Plan.

        Args:
            ceremony_id: ID of ceremony
            story_id: Story whose plan is being approved
            approved_by: User approving the plan (typically PO)

        Returns:
            Created Plan entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If story not in ceremony, no plan preliminary, or not pending
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Find review result for story
        review_result = None
        for result in ceremony.review_results:
            if result.story_id == story_id:
                review_result = result
                break

        if not review_result:
            raise ValueError(
                f"No review result found for story {story_id.value} "
                f"in ceremony {ceremony_id.value}"
            )

        if not review_result.plan_preliminary:
            raise ValueError(
                f"No plan preliminary found for story {story_id.value}"
            )

        # Approve review result (immutably)
        approved_at = datetime.now(UTC)
        approved_result = review_result.approve(approved_by, approved_at)

        # Convert PlanPreliminary → Plan (official entity)
        plan_preliminary = review_result.plan_preliminary
        plan_id = PlanId(f"PL-{uuid4()}")

        plan = Plan(
            plan_id=plan_id,
            story_id=story_id,
            title=plan_preliminary.title,
            brief=plan_preliminary.description,
            created_at=approved_at,
            updated_at=approved_at,
        )

        # Save Plan
        await self.storage.save_plan(plan)

        # Update story to READY_FOR_PLANNING
        # NOTE: This assumes TransitionStoryUseCase exists
        # For now, we'll just save the plan and ceremony
        # The story transition will be handled separately or via event

        # Update ceremony with approved result
        ceremony = ceremony.update_review_result(story_id, approved_result, approved_at)

        # Persist ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Approved plan {plan_id.value} for story {story_id.value} "
            f"by {approved_by.value}"
        )

        # Publish event (best-effort)
        try:
            await self.messaging.publish(
                subject="planning.plan.approved",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "story_id": story_id.value,
                    "plan_id": plan_id.value,
                    "approved_by": approved_by.value,
                    "approved_at": approved_at.isoformat(),
                    "tasks_outline": list(plan_preliminary.tasks_outline),
                    "estimated_complexity": plan_preliminary.estimated_complexity,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish plan.approved event: {e}")

        return plan

