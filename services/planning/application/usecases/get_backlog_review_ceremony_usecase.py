"""GetBacklogReviewCeremonyUseCase - Retrieve ceremony by ID.

Use Case (Application Layer):
- Simple query use case
- Depends on StoragePort only
"""

import logging
from dataclasses import dataclass

from planning.application.ports import StoragePort
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)

logger = logging.getLogger(__name__)


@dataclass
class GetBacklogReviewCeremonyUseCase:
    """
    Retrieve a backlog review ceremony by ID.

    This use case:
    1. Validates ceremony ID
    2. Queries storage
    3. Returns ceremony or None

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - Returns domain entity
    - No infrastructure dependencies
    """

    storage: StoragePort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
    ) -> BacklogReviewCeremony | None:
        """
        Get backlog review ceremony by ID.

        Args:
            ceremony_id: ID of ceremony to retrieve

        Returns:
            BacklogReviewCeremony if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if ceremony:
            logger.info(f"Retrieved ceremony: {ceremony_id.value}")
        else:
            logger.info(f"Ceremony not found: {ceremony_id.value}")

        return ceremony

