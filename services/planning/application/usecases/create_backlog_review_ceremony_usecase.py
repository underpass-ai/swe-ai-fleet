"""CreateBacklogReviewCeremonyUseCase - Create backlog review ceremony.

Use Case (Application Layer):
- Orchestrates domain logic
- Depends on ports (interfaces)
- NO infrastructure dependencies
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)

logger = logging.getLogger(__name__)


@dataclass
class CreateBacklogReviewCeremonyUseCase:
    """
    Create a new backlog review ceremony.

    This use case:
    1. Generates unique ceremony ID
    2. Creates BacklogReviewCeremony entity (DRAFT status)
    3. Persists to storage (Neo4j + Valkey)
    4. Publishes planning.backlog_review.created event
    5. Returns created ceremony

    Following Hexagonal Architecture:
    - Depends on ports (StoragePort, MessagingPort)
    - Returns domain entity (BacklogReviewCeremony)
    - No infrastructure dependencies
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        created_by: UserName,
        story_ids: tuple[StoryId, ...] = (),
    ) -> BacklogReviewCeremony:
        """
        Create backlog review ceremony.

        Args:
            created_by: PO user creating the ceremony
            story_ids: Optional pre-selected stories (can be empty)

        Returns:
            Created BacklogReviewCeremony entity (DRAFT status)

        Raises:
            ValueError: If validation fails (created_by empty, etc.)
            StorageError: If persistence fails
            MessagingError: If event publishing fails (non-blocking)
        """
        # Generate unique ceremony ID
        ceremony_id = BacklogReviewCeremonyId(f"BRC-{uuid4()}")

        # Create timestamps
        now = datetime.now(UTC)

        # Create ceremony entity (DRAFT status)
        ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=story_ids,
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=now,
            updated_at=now,
        )

        # Persist to storage
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Created backlog review ceremony: {ceremony_id.value} "
            f"by {created_by.value} with {len(story_ids)} stories"
        )

        # Publish event (non-blocking, best-effort)
        try:
            await self.messaging.publish(
                subject="planning.backlog_review.created",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "created_by": created_by.value,
                    "story_ids": [sid.value for sid in story_ids],
                    "status": ceremony.status.to_string(),
                    "created_at": ceremony.created_at.isoformat(),
                },
            )
        except Exception as e:
            # Log error but don't fail the use case
            logger.warning(
                f"Failed to publish planning.backlog_review.created event: {e}"
            )

        return ceremony

