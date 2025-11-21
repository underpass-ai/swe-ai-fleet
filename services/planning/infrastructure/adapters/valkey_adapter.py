"""Valkey (Redis-compatible) adapter for Planning Service - Permanent Storage."""

import asyncio
import logging
import os
from dataclasses import dataclass, field

import redis
from planning.application.ports import StoragePort
from planning.domain import Story, StoryId, StoryList, StoryState, StoryStateEnum
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys
from planning.infrastructure.mappers.story_valkey_mapper import StoryValkeyMapper

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValkeyConfig:
    """
    Valkey connection configuration.

    Persistence Configuration (K8s ConfigMap):
    - AOF (Append-Only File): appendonly yes
    - RDB Snapshots: save 900 1, save 300 10, save 60 10000
    - This ensures data survives pod restarts
    """

    host: str = field(default_factory=lambda: os.getenv("VALKEY_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("VALKEY_PORT", "6379")))
    db: int = 0
    decode_responses: bool = True


class ValkeyStorageAdapter(StoragePort):
    """
    Valkey (Redis-compatible) permanent storage adapter for Planning Service.

    Storage Strategy:
    - Valkey with AOF + RDB persistence (configured in K8s)
    - No TTL (permanent storage)
    - Efficient queries with Redis data structures

    Data Model:
    - Hash: planning:story:{story_id} → Story fields
    - Set: planning:stories:all → All story IDs
    - Set: planning:stories:state:{state} → Story IDs by state
    - String: planning:story:{story_id}:state → Current FSM state (denormalized for fast lookup)

    Persistence (K8s Valkey ConfigMap):
    - AOF enabled: appendonly yes
    - RDB snapshots: save 900 1, save 300 10, save 60 10000
    - Data survives pod restarts
    """

    def __init__(self, config: ValkeyConfig | None = None):
        """Initialize Valkey permanent storage adapter."""
        self.config = config or ValkeyConfig()

        # Create Redis client (Valkey is Redis-compatible)
        self.client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
        )

        # Test connection
        self.client.ping()

        logger.info(
            f"Valkey permanent storage initialized: {self.config.host}:{self.config.port}"
        )

    def close(self) -> None:
        """Close Valkey connection."""
        self.client.close()
        logger.info("Valkey connection closed")

    # Key generation delegated to ValkeyKeys static class
    def _story_hash_key(self, story_id: StoryId) -> str:
        """Generate hash key for story details."""
        return ValkeyKeys.story_hash(story_id)

    def _story_state_key(self, story_id: StoryId) -> str:
        """Generate key for FSM state (fast lookup)."""
        return ValkeyKeys.story_state(story_id)

    def _all_stories_set_key(self) -> str:
        """Key for set containing all story IDs."""
        return ValkeyKeys.all_stories()

    def _stories_by_state_set_key(self, state: StoryState) -> str:
        """Key for set containing story IDs by state."""
        return ValkeyKeys.stories_by_state(state)

    async def save_story(self, story: Story) -> None:
        """
        Persist story details to Valkey (permanent storage).

        Stores:
        - Hash with all story fields (permanent, no TTL)
        - FSM state string for fast lookups
        - Story ID in sets for indexing

        Args:
            story: Story to persist.
        """
        # Store story as hash (all fields) using mapper
        hash_key = self._story_hash_key(story.story_id)
        story_data = StoryValkeyMapper.to_dict(story)
        self.client.hset(hash_key, mapping=story_data)

        # Store FSM state separately for fast lookups
        self.client.set(
            self._story_state_key(story.story_id),
            story.state.to_string(),  # Tell, Don't Ask
        )

        # Add to all stories set
        self.client.sadd(self._all_stories_set_key(), story.story_id.value)

        # Add to state-specific set
        self.client.sadd(
            self._stories_by_state_set_key(story.state),
            story.story_id.value,
        )

        logger.info(f"Story saved to Valkey: {story.story_id}")

    async def get_story(self, story_id: StoryId) -> Story | None:
        """
        Retrieve story from Valkey permanent storage.

        Args:
            story_id: ID of story to retrieve.

        Returns:
            Story if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_story_sync, story_id)

    def _get_story_sync(self, story_id: StoryId) -> Story | None:
        """Synchronous get_story for thread execution."""
        hash_key = self._story_hash_key(story_id)
        data = self.client.hgetall(hash_key)

        if not data:
            logger.debug(f"Story not found in Valkey: {story_id}")
            return None

        logger.debug(f"Story retrieved from Valkey: {story_id}")

        # Convert hash to Story entity using mapper
        return StoryValkeyMapper.from_dict(data)

    async def list_stories(
        self,
        state_filter: StoryState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> StoryList:
        """
        List stories from Valkey with optional filtering.

        Args:
            state_filter: Filter by state (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            StoryList collection.
        """
        return await asyncio.to_thread(
            self._list_stories_sync,
            state_filter,
            limit,
            offset,
        )

    def _list_stories_sync(
        self,
        state_filter: StoryState | None,
        limit: int,
        offset: int,
    ) -> StoryList:
        """Synchronous list_stories for thread execution."""
        # Get story IDs (filtered or all)
        if state_filter:
            story_ids = list(self.client.smembers(
                self._stories_by_state_set_key(state_filter)
            ))
        else:
            story_ids = list(self.client.smembers(self._all_stories_set_key()))

        # Sort by ID (creation order approximation)
        story_ids.sort()

        # Apply pagination
        paginated_ids = story_ids[offset:offset + limit]

        # Retrieve full stories synchronously
        stories = []
        for story_id_str in paginated_ids:
            story = self._get_story_sync(StoryId(story_id_str))
            if story:
                stories.append(story)

        return StoryList.from_list(stories)

    async def update_story(self, story: Story) -> None:
        """
        Update story in Valkey.

        Updates:
        - Hash with all fields
        - State-specific sets (if state changed)

        Args:
            story: Updated story.
        """
        # Get old state to update sets if needed
        old_state_str = self.client.hget(
            self._story_hash_key(story.story_id),
            "state"
        )

        # Update hash using mapper
        hash_key = self._story_hash_key(story.story_id)
        story_data = StoryValkeyMapper.to_dict(story)
        self.client.hset(hash_key, mapping=story_data)

        # Update FSM state
        self.client.set(
            self._story_state_key(story.story_id),
            story.state.to_string(),  # Tell, Don't Ask
        )

        # If state changed, update state sets
        if old_state_str and old_state_str != story.state.to_string():
            old_state = StoryState(StoryStateEnum(old_state_str))

            # Remove from old state set
            self.client.srem(
                self._stories_by_state_set_key(old_state),
                story.story_id.value,
            )

            # Add to new state set
            self.client.sadd(
                self._stories_by_state_set_key(story.state),
                story.story_id.value,
            )

        logger.info(f"Story updated in Valkey: {story.story_id}")

    async def delete_story(self, story_id: StoryId) -> None:
        """
        Delete story from Valkey permanent storage.

        Deletes:
        - Hash with all fields
        - FSM state string
        - Story ID from sets

        Args:
            story_id: ID of story to delete.
        """
        # Get current state to remove from state set
        state_str = self.client.get(self._story_state_key(story_id))

        # Delete hash
        self.client.delete(self._story_hash_key(story_id))

        # Delete FSM state
        self.client.delete(self._story_state_key(story_id))

        # Remove from all stories set
        self.client.srem(self._all_stories_set_key(), story_id.value)

        # Remove from state-specific set
        if state_str:
            state = StoryState(StoryStateEnum(state_str))
            self.client.srem(
                self._stories_by_state_set_key(state),
                story_id.value,
            )

        logger.info(f"Story deleted from Valkey: {story_id}")

