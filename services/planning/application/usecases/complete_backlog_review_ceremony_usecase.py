"""CompleteBacklogReviewCeremonyUseCase - Complete ceremony.

Use Case (Application Layer):
- Finalize ceremony after PO has reviewed all plans
- Publishes completion event
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)

logger = logging.getLogger(__name__)


@dataclass
class CompleteBacklogReviewCeremonyUseCase:
    """
    Complete a backlog review ceremony.

    This use case:
    1. Retrieves ceremony
    2. Validates all review results have been approved/rejected
    3. Marks ceremony as completed
    4. Publishes planning.backlog_review.ceremony.completed event
    5. Returns completed ceremony

    Following Hexagonal Architecture:
    - Depends on StoragePort and MessagingPort
    - Returns domain entity
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
    ) -> BacklogReviewCeremony:
        """
        Complete backlog review ceremony.

        Args:
            ceremony_id: ID of ceremony to complete

        Returns:
            Completed BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony cannot be completed (wrong status or pending reviews)
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Validate all reviews are decided (not PENDING)
        for review_result in ceremony.review_results:
            if review_result.approval_status.is_pending():
                raise ValueError(
                    f"Cannot complete ceremony: Story {review_result.story_id.value} "
                    "still has pending approval"
                )

        # Complete ceremony (immutably)
        completed_at = datetime.now(UTC)
        ceremony = ceremony.complete(completed_at)

        # Persist
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(f"Completed backlog review ceremony: {ceremony_id.value}")

        # Publish event (best-effort)
        try:
            await self.messaging.publish(
                subject="planning.backlog_review.ceremony.completed",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "completed_at": completed_at.isoformat(),
                    "total_stories": len(ceremony.story_ids),
                    "approved_count": sum(
                        1 for r in ceremony.review_results if r.approval_status.is_approved()
                    ),
                    "rejected_count": sum(
                        1 for r in ceremony.review_results if r.approval_status.is_rejected()
                    ),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.completed event: {e}")

        return ceremony

