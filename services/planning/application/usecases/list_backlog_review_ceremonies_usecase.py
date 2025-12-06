"""ListBacklogReviewCeremoniesUseCase - List ceremonies with optional filtering.

Use Case (Application Layer):
- List backlog review ceremonies with optional filters
- Supports filtering by status and created_by
- Supports pagination
- Filters applied in memory (can be optimized later to storage layer)
"""

import logging
from dataclasses import dataclass

from planning.application.ports import StoragePort
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)

logger = logging.getLogger(__name__)


@dataclass
class ListBacklogReviewCeremoniesUseCase:
    """
    List backlog review ceremonies with optional filtering.

    This use case:
    1. Validates pagination parameters
    2. Queries storage for all ceremonies
    3. Applies filters in memory (status_filter, created_by)
    4. Returns filtered list

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - Returns list of domain entities
    - No infrastructure dependencies

    Note: Filtering is done in memory for simplicity.
    For better performance with large datasets, consider moving filters to storage layer.
    """

    storage: StoragePort

    async def execute(
        self,
        status_filter: BacklogReviewCeremonyStatus | None = None,
        created_by: UserName | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BacklogReviewCeremony]:
        """
        List backlog review ceremonies with optional filtering.

        Args:
            status_filter: Filter by ceremony status (optional)
            created_by: Filter by creator user (optional)
            limit: Maximum number of results (default 100, max 1000)
            offset: Offset for pagination (default 0)

        Returns:
            List of BacklogReviewCeremony entities matching filters

        Raises:
            ValueError: If limit or offset is invalid
            StorageError: If query fails
        """
        # Validate pagination parameters
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")

        if limit > 1000:
            raise ValueError(f"limit must be <= 1000, got {limit}")

        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")

        # Query storage (get all ceremonies, we'll filter in memory)
        # Note: For better performance, filters could be moved to storage layer
        all_ceremonies = await self.storage.list_backlog_review_ceremonies(
            limit=10000,  # Get more than needed to apply filters
            offset=0,
        )

        # Apply filters in memory
        filtered_ceremonies = all_ceremonies

        if status_filter:
            filtered_ceremonies = [
                c for c in filtered_ceremonies if c.status == status_filter
            ]

        if created_by:
            filtered_ceremonies = [
                c for c in filtered_ceremonies if c.created_by == created_by
            ]

        # Apply pagination
        paginated_ceremonies = filtered_ceremonies[offset : offset + limit]

        logger.info(
            f"Listed {len(paginated_ceremonies)} ceremonies "
            f"(filtered from {len(all_ceremonies)} total, "
            f"status_filter={status_filter.to_string() if status_filter else None}, "
            f"created_by={created_by.value if created_by else None})"
        )

        return paginated_ceremonies
