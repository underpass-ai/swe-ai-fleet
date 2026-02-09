"""RejectReviewPlanUseCase - PO rejects plan preliminary.

Use Case (Application Layer):
- PO rejects a plan from ceremony review
- Updates review result status
- Publishes rejection event
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


@dataclass
class RejectReviewPlanUseCase:
    """
    Reject a plan preliminary from backlog review ceremony.

    This use case (Human-in-the-Loop):
    1. Retrieves ceremony
    2. Finds StoryReviewResult for story
    3. Rejects review result (sets approval_status=REJECTED)
    4. Updates ceremony with rejected result
    5. Publishes planning.plan.rejected event
    6. Returns updated ceremony

    Following Hexagonal Architecture:
    - Depends on StoragePort and MessagingPort
    - Returns domain entity
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        rejected_by: UserName,
        rejection_reason: str,
    ) -> BacklogReviewCeremony:
        """
        Reject plan preliminary from ceremony review.

        Args:
            ceremony_id: ID of ceremony
            story_id: Story whose plan is being rejected
            rejected_by: User rejecting the plan (typically PO)
            rejection_reason: Reason for rejection

        Returns:
            Updated BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If story not in ceremony or review not pending
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

        # Reject review result (immutably)
        rejected_result = review_result.reject()

        # Update ceremony with rejected result
        updated_at = datetime.now(UTC)
        ceremony = ceremony.update_review_result(story_id, rejected_result, updated_at)

        # Persist
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Rejected plan for story {story_id.value} in ceremony {ceremony_id.value} "
            f"by {rejected_by.value}"
        )

        # Publish event (best-effort)
        try:
            await self.messaging.publish_event(
                subject="planning.plan.rejected",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "story_id": story_id.value,
                    "rejected_by": rejected_by.value,
                    "rejection_reason": rejection_reason,
                    "rejected_at": updated_at.isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish plan.rejected event: {e}")

        return ceremony
