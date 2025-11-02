"""Neo4j adapter for Planning Service - Graph structure only."""

import asyncio
import logging
import os
from dataclasses import dataclass, field

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, TransientError

from planning.domain import StoryId, StoryState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration."""

    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password"))
    database: str | None = field(default_factory=lambda: os.getenv("NEO4J_DATABASE") or None)
    max_retries: int = 3
    base_backoff_s: float = 0.25


class Neo4jAdapter:
    """
    Neo4j adapter for graph structure in Planning Service.

    Responsibility:
    - Store graph nodes (Story) with minimal properties (id, state)
    - Store relationships (CREATED_BY, HAS_TASK, etc.)
    - Enable graph navigation and rehydration
    - Support alternative solutions queries

    NOT Responsible for:
    - Storing detailed content (title, brief, etc.) → Valkey
    """

    def __init__(self, config: Neo4jConfig | None = None):
        """Initialize Neo4j adapter."""
        self.config = config or Neo4jConfig()
        self.driver: Driver = GraphDatabase.driver(
            self.config.uri,
            auth=(self.config.user, self.config.password)
        )
        self._init_constraints()
        logger.info(f"Neo4j graph adapter initialized: {self.config.uri}")

    def close(self) -> None:
        """Close Neo4j driver."""
        self.driver.close()
        logger.info("Neo4j driver closed")

    def _session(self) -> Session:
        """Create a new session."""
        if self.config.database:
            return self.driver.session(database=self.config.database)
        return self.driver.session()

    def _retry_operation(self, fn, *args, **kwargs):
        """Retry operations on transient errors with exponential backoff."""
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except (ServiceUnavailable, TransientError) as e:
                if attempt >= self.config.max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise

                backoff = self.config.base_backoff_s * (2 ** attempt)
                logger.warning(f"Retrying after {backoff}s (attempt {attempt + 1}): {e}")
                import time
                time.sleep(backoff)
                attempt += 1

    def _init_constraints(self) -> None:
        """Initialize Neo4j constraints."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Story) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE s.id IS UNIQUE",
        ]

        def _tx(tx):
            for constraint in constraints:
                tx.run(constraint)

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

        logger.info("Neo4j constraints initialized")

    async def create_story_node(
        self,
        story_id: StoryId,
        created_by: str,
        initial_state: StoryState,
    ) -> None:
        """
        Create Story node in graph with minimal properties.

        Creates:
        - Story node with id and current state
        - User node if doesn't exist
        - CREATED_BY relationship

        Args:
            story_id: Story ID.
            created_by: User who created the story.
            initial_state: Initial FSM state.
        """
        await asyncio.to_thread(
            self._create_story_node_sync,
            story_id,
            created_by,
            initial_state,
        )
        logger.info(f"Story node created in graph: {story_id}")

    def _create_story_node_sync(
        self,
        story_id: StoryId,
        created_by: str,
        initial_state: StoryState,
    ) -> None:
        """Synchronous node creation."""
        cypher = """
        // Create or update Story node (minimal properties)
        MERGE (s:Story {id: $story_id})
        SET s.state = $state

        // Create or update User node
        MERGE (u:User {id: $created_by})

        // Create CREATED_BY relationship
        MERGE (u)-[:CREATED]->(s)

        RETURN s
        """

        def _tx(tx):
            tx.run(
                cypher,
                story_id=story_id.value,
                state=initial_state.value.value,
                created_by=created_by,
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def update_story_state(
        self,
        story_id: StoryId,
        new_state: StoryState,
    ) -> None:
        """
        Update Story node's state in graph.

        Args:
            story_id: Story ID.
            new_state: New FSM state.
        """
        await asyncio.to_thread(
            self._update_story_state_sync,
            story_id,
            new_state,
        )
        logger.info(f"Story state updated in graph: {story_id} → {new_state}")

    def _update_story_state_sync(
        self,
        story_id: StoryId,
        new_state: StoryState,
    ) -> None:
        """Synchronous state update."""
        cypher = """
        MATCH (s:Story {id: $story_id})
        SET s.state = $state
        RETURN s
        """

        def _tx(tx):
            result = tx.run(
                cypher,
                story_id=story_id.value,
                state=new_state.value.value,
            )
            return result.single() is not None

        with self._session() as session:
            found = self._retry_operation(session.execute_write, _tx)

        if not found:
            raise ValueError(f"Story node not found in graph: {story_id}")

    async def delete_story_node(self, story_id: StoryId) -> None:
        """
        Delete Story node from graph.

        Args:
            story_id: Story ID to delete.
        """
        await asyncio.to_thread(self._delete_story_node_sync, story_id)
        logger.info(f"Story node deleted from graph: {story_id}")

    def _delete_story_node_sync(self, story_id: StoryId) -> None:
        """Synchronous node deletion."""
        cypher = """
        MATCH (s:Story {id: $story_id})
        DETACH DELETE s
        """

        def _tx(tx):
            tx.run(cypher, story_id=story_id.value)

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def get_story_ids_by_state(self, state: StoryState) -> list[str]:
        """
        Get all story IDs in a specific state (graph query).

        Args:
            state: FSM state to filter by.

        Returns:
            List of story IDs.
        """
        return await asyncio.to_thread(
            self._get_story_ids_by_state_sync,
            state,
        )

    def _get_story_ids_by_state_sync(self, state: StoryState) -> list[str]:
        """Synchronous query for story IDs by state."""
        cypher = """
        MATCH (s:Story {state: $state})
        RETURN s.id as story_id
        ORDER BY s.id
        """

        def _tx(tx):
            result = tx.run(cypher, state=state.value.value)
            return [record["story_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

