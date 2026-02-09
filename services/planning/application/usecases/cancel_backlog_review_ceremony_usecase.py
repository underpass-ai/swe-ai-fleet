"""CancelBacklogReviewCeremonyUseCase - Cancel ceremony.

Use Case (Application Layer):
- Cancel ceremony before completion
- Publishes cancellation event
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

logger = logging.getLogger(__name__)


@dataclass
class CancelBacklogReviewCeremonyUseCase:
    """
    Cancel a backlog review ceremony.

    This use case:
    1. Retrieves ceremony
    2. Validates ceremony can be cancelled (not already completed)
    3. Marks ceremony as cancelled
    4. Publishes planning.backlog_review.ceremony.cancelled event
    5. Returns cancelled ceremony

    Following Hexagonal Architecture:
    - Depends on StoragePort and MessagingPort
    - Returns domain entity
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        cancelled_by: UserName,
    ) -> BacklogReviewCeremony:
        """
        Cancel backlog review ceremony.

        Args:
            ceremony_id: ID of ceremony to cancel
            cancelled_by: User cancelling the ceremony (typically PO)

        Returns:
            Cancelled BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony is already completed
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Cancel ceremony (immutably)
        updated_at = datetime.now(UTC)
        ceremony = ceremony.cancel(updated_at)

        # Persist
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Cancelled backlog review ceremony: {ceremony_id.value} "
            f"by {cancelled_by.value}"
        )

        # Publish event (best-effort)
        try:
            await self.messaging.publish_event(
                subject="planning.backlog_review.ceremony.cancelled",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "cancelled_by": cancelled_by.value,
                    "cancelled_at": updated_at.isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.cancelled event: {e}")

        return ceremony
