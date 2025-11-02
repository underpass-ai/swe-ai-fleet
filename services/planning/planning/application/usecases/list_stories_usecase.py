"""List Stories use case."""

from dataclasses import dataclass

from planning.application.ports import StoragePort
from planning.domain import StoryList, StoryState


@dataclass
class ListStoriesUseCase:
    """
    Use Case: List stories with optional filtering.

    Business Rules:
    - Support filtering by state
    - Support pagination
    - Default limit is 100 stories

    Dependencies:
    - StoragePort: Query stories
    """

    storage: StoragePort

    async def execute(
        self,
        state_filter: StoryState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> StoryList:
        """
        List stories with optional filtering.

        Args:
            state_filter: Filter by state (optional).
            limit: Maximum number of results (default 100).
            offset: Offset for pagination (default 0).

        Returns:
            StoryList collection matching criteria.

        Raises:
            ValueError: If limit or offset is invalid.
            StorageError: If query fails.
        """
        # Validate pagination parameters
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")

        if limit > 1000:
            raise ValueError(f"limit must be <= 1000, got {limit}")

        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")

        # Query storage
        stories = await self.storage.list_stories(
            state_filter=state_filter,
            limit=limit,
            offset=offset,
        )

        return stories

