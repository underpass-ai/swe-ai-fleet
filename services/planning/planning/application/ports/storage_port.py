"""Storage port for Planning Service (dual persistence: Neo4j + Valkey)."""

from typing import Protocol

from planning.domain import Story, StoryId, StoryState


class StoragePort(Protocol):
    """
    Port (interface) for story persistence.

    Dual Persistence Strategy:
    - Neo4j: Graph relationships, historical data, complex queries
    - Valkey: Current state, FSM cache, fast reads

    Implementations will handle coordination between both stores.
    """

    async def save_story(self, story: Story) -> None:
        """
        Persist a story to both Neo4j and Valkey.

        Neo4j:
        - Store story node with all attributes
        - Create relationships (created_by, dependencies, etc.)

        Valkey:
        - Cache current state for fast FSM lookups
        - Set TTL if needed

        Args:
            story: Story to persist.

        Raises:
            StorageError: If persistence fails.
        """
        ...

    async def get_story(self, story_id: StoryId) -> Story | None:
        """
        Retrieve a story by ID.

        Strategy:
        1. Try Valkey cache first (fast)
        2. If miss, query Neo4j and update cache

        Args:
            story_id: ID of story to retrieve.

        Returns:
            Story if found, None otherwise.

        Raises:
            StorageError: If retrieval fails.
        """
        ...

    async def list_stories(
        self,
        state_filter: StoryState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Story]:
        """
        List stories with optional filtering.

        Strategy:
        - Query Neo4j for complex filters
        - Simple queries may use Valkey if cached

        Args:
            state_filter: Filter by state (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of stories matching criteria.

        Raises:
            StorageError: If query fails.
        """
        ...

    async def update_story(self, story: Story) -> None:
        """
        Update an existing story in both stores.

        Neo4j:
        - Update node properties
        - Maintain version history if needed

        Valkey:
        - Update cached state
        - Invalidate related caches

        Args:
            story: Updated story.

        Raises:
            StorageError: If update fails.
            StoryNotFoundError: If story doesn't exist.
        """
        ...

    async def delete_story(self, story_id: StoryId) -> None:
        """
        Delete a story from both stores.

        Neo4j:
        - Delete node and relationships

        Valkey:
        - Remove from cache

        Args:
            story_id: ID of story to delete.

        Raises:
            StorageError: If deletion fails.
        """
        ...

