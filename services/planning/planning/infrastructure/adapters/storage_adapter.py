"""Composite storage adapter coordinating Neo4j (graph) + Valkey (details)."""

import logging

from planning.application.ports import StoragePort
from planning.domain import Story, StoryId, StoryState
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter, ValkeyConfig

logger = logging.getLogger(__name__)


class StorageAdapter(StoragePort):
    """
    Composite storage adapter implementing the dual persistence pattern.
    
    Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                 StorageAdapter                       │
    ├─────────────────────────────────────────────────────┤
    │                                                      │
    │  Neo4j (Graph)          Valkey (Details)            │
    │  ├─ Nodes (Story)       ├─ Hash (all fields)        │
    │  ├─ Relationships       ├─ Sets (indexing)          │
    │  ├─ State (minimal)     ├─ Permanent (AOF+RDB)      │
    │  └─ Observability       └─ Fast reads               │
    │                                                      │
    └─────────────────────────────────────────────────────┘
    
    Neo4j Responsibility:
    - Graph structure (Story nodes with id + state)
    - Relationships (CREATED_BY, HAS_TASK, etc.)
    - Enable rehydration from specific node
    - Support alternative solutions queries
    - Observability and graph traversal
    
    Valkey Responsibility:
    - Detailed content (title, brief, timestamps, etc.)
    - Permanent storage (AOF + RDB persistence)
    - Fast reads/writes
    - Indexing (sets by state, all stories, etc.)
    
    Write Path:
    1. Save details to Valkey
    2. Create/update node in Neo4j graph
    
    Read Path:
    - Retrieve from Valkey (has all details)
    
    Query Path (list, filter):
    - Use Valkey sets for fast filtering
    - Use Neo4j for graph queries (if needed for relationships)
    """
    
    def __init__(
        self,
        neo4j_config: Neo4jConfig | None = None,
        valkey_config: ValkeyConfig | None = None,
    ):
        """
        Initialize composite storage adapter.
        
        Args:
            neo4j_config: Neo4j configuration (optional, uses env vars).
            valkey_config: Valkey configuration (optional, uses env vars).
        """
        self.neo4j = Neo4jAdapter(config=neo4j_config)
        self.valkey = ValkeyStorageAdapter(config=valkey_config)
        
        logger.info("Composite storage initialized (Neo4j graph + Valkey details)")
    
    def close(self) -> None:
        """Close all connections."""
        self.neo4j.close()
        self.valkey.close()
        logger.info("Storage adapter closed")
    
    async def save_story(self, story: Story) -> None:
        """
        Persist story to Neo4j (graph) + Valkey (details).
        
        Operations:
        1. Save full details to Valkey
        2. Create graph node in Neo4j (minimal properties)
        
        Args:
            story: Story to persist.
        
        Raises:
            Exception: If persistence fails.
        """
        # 1. Save details to Valkey (permanent storage)
        await self.valkey.save_story(story)
        
        # 2. Create graph node in Neo4j (structure only)
        await self.neo4j.create_story_node(
            story_id=story.story_id,
            created_by=story.created_by,
            initial_state=story.state,
        )
        
        logger.info(f"Story saved (dual): {story.story_id}")
    
    async def get_story(self, story_id: StoryId) -> Story | None:
        """
        Retrieve story from Valkey.
        
        Note: Valkey has all details, Neo4j only has graph structure.
        
        Args:
            story_id: ID of story to retrieve.
        
        Returns:
            Story if found, None otherwise.
        """
        return await self.valkey.get_story(story_id)
    
    async def list_stories(
        self,
        state_filter: StoryState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Story]:
        """
        List stories from Valkey.
        
        Uses Valkey sets for efficient filtering by state.
        
        Args:
            state_filter: Filter by state (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.
        
        Returns:
            List of stories.
        """
        return await self.valkey.list_stories(
            state_filter=state_filter,
            limit=limit,
            offset=offset,
        )
    
    async def update_story(self, story: Story) -> None:
        """
        Update story in Valkey + Neo4j.
        
        Operations:
        1. Update details in Valkey
        2. Update state in Neo4j graph (if changed)
        
        Args:
            story: Updated story.
        
        Raises:
            ValueError: If story doesn't exist.
        """
        # 1. Update details in Valkey
        await self.valkey.update_story(story)
        
        # 2. Update state in Neo4j graph
        await self.neo4j.update_story_state(
            story_id=story.story_id,
            new_state=story.state,
        )
        
        logger.info(f"Story updated (dual): {story.story_id}")
    
    async def delete_story(self, story_id: StoryId) -> None:
        """
        Delete story from Valkey + Neo4j.
        
        Operations:
        1. Delete from Valkey
        2. Delete node from Neo4j graph
        
        Args:
            story_id: ID of story to delete.
        """
        # 1. Delete from Valkey
        await self.valkey.delete_story(story_id)
        
        # 2. Delete node from Neo4j graph
        await self.neo4j.delete_story_node(story_id)
        
        logger.info(f"Story deleted (dual): {story_id}")

