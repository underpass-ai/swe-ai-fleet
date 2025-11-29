"""Neo4j adapter for Planning Service - Graph structure only."""

import asyncio
import logging

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
from planning.domain import StoryId, StoryState
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.infrastructure.adapters.neo4j_config import Neo4jConfig
from planning.infrastructure.adapters.neo4j_queries import Neo4jConstraints, Neo4jQuery

logger = logging.getLogger(__name__)


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
        def _tx(tx):
            for constraint in Neo4jConstraints.all():
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
        def _tx(tx):
            tx.run(
                Neo4jQuery.CREATE_STORY_NODE.value,
                story_id=story_id.value,
                state=initial_state.to_string(),  # Tell, Don't Ask
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
        def _tx(tx):
            result =             tx.run(
                Neo4jQuery.UPDATE_STORY_STATE.value,
                story_id=story_id.value,
                state=new_state.to_string(),  # Tell, Don't Ask
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
        def _tx(tx):
            tx.run(
                Neo4jQuery.DELETE_STORY_NODE.value,
                story_id=story_id.value,
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def create_task_dependencies(
        self,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        """
        Create DEPENDS_ON relationships between tasks in Neo4j graph.

        Args:
            dependencies: Tuple of dependency edges to persist

        Raises:
            ValueError: If any task node doesn't exist
        """
        if not dependencies:
            return  # Nothing to persist

        await asyncio.to_thread(
            self._create_task_dependencies_sync,
            dependencies,
        )
        logger.info(f"Created {len(dependencies)} task dependencies in graph")

    def _create_task_dependencies_sync(
        self,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        """Synchronous dependency creation."""
        def _tx(tx):
            for dep in dependencies:
                result = tx.run(
                    Neo4jQuery.CREATE_TASK_DEPENDENCY.value,
                    from_task_id=dep.from_task_id.value,
                    to_task_id=dep.to_task_id.value,
                    reason=dep.reason.value,
                )
                if result.single() is None:
                    raise ValueError(
                        f"Failed to create dependency: {dep.from_task_id.value} -> {dep.to_task_id.value}"
                    )

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
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_STORY_IDS_BY_STATE.value,
                state=state.to_string(),  # Tell, Don't Ask
            )
            return [record["story_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

    # ========== Project Methods ==========

    async def create_project_node(
        self,
        project_id: str,
        name: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """
        Create Project node in graph with minimal properties.

        Args:
            project_id: Project ID.
            name: Project name.
            status: Project status (string value).
            created_at: ISO format timestamp.
            updated_at: ISO format timestamp.
        """
        await asyncio.to_thread(
            self._create_project_node_sync,
            project_id,
            name,
            status,
            created_at,
            updated_at,
        )
        logger.info(f"Project node created in graph: {project_id}")

    def _create_project_node_sync(
        self,
        project_id: str,
        name: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """Synchronous node creation."""
        def _tx(tx):
            tx.run(
                Neo4jQuery.CREATE_PROJECT_NODE.value,
                project_id=project_id,
                name=name,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        updated_at: str,
    ) -> None:
        """
        Update Project node's status in graph.

        Args:
            project_id: Project ID.
            status: New status (string value).
            updated_at: ISO format timestamp.
        """
        await asyncio.to_thread(
            self._update_project_status_sync,
            project_id,
            status,
            updated_at,
        )
        logger.info(f"Project status updated in graph: {project_id} → {status}")

    def _update_project_status_sync(
        self,
        project_id: str,
        status: str,
        updated_at: str,
    ) -> None:
        """Synchronous status update."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.UPDATE_PROJECT_STATUS.value,
                project_id=project_id,
                status=status,
                updated_at=updated_at,
            )
            return result.single() is not None

        with self._session() as session:
            found = self._retry_operation(session.execute_write, _tx)

        if not found:
            raise ValueError(f"Project node not found in graph: {project_id}")

    async def get_project_ids_by_status(self, status: str) -> list[str]:
        """
        Get all project IDs in a specific status (graph query).

        Args:
            status: Status to filter by (string value).

        Returns:
            List of project IDs.
        """
        return await asyncio.to_thread(
            self._get_project_ids_by_status_sync,
            status,
        )

    def _get_project_ids_by_status_sync(self, status: str) -> list[str]:
        """Synchronous query for project IDs by status."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_PROJECT_IDS_BY_STATUS.value,
                status=status,
            )
            return [record["project_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

    # ========== Epic Methods ==========

    async def create_epic_node(
        self,
        epic_id: str,
        project_id: str,
        name: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """
        Create Epic node in graph and link to Project.

        Args:
            epic_id: Epic ID.
            project_id: Parent Project ID.
            name: Epic title/name.
            status: Epic status.
            created_at: ISO timestamp.
            updated_at: ISO timestamp.
        """
        await asyncio.to_thread(
            self._create_epic_node_sync,
            epic_id,
            project_id,
            name,
            status,
            created_at,
            updated_at,
        )
        logger.info(f"Epic node created in graph: {epic_id} (Project: {project_id})")

    def _create_epic_node_sync(
        self,
        epic_id: str,
        project_id: str,
        name: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """Synchronous Epic node creation."""
        def _tx(tx):
            tx.run(
                Neo4jQuery.CREATE_EPIC_NODE.value,
                epic_id=epic_id,
                project_id=project_id,
                name=name,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def update_epic_status(
        self,
        epic_id: str,
        status: str,
        updated_at: str,
    ) -> None:
        """
        Update Epic status in graph.

        Args:
            epic_id: Epic ID.
            status: New status.
            updated_at: ISO timestamp.
        """
        await asyncio.to_thread(
            self._update_epic_status_sync,
            epic_id,
            status,
            updated_at,
        )
        logger.info(f"Epic status updated in graph: {epic_id} → {status}")

    def _update_epic_status_sync(
        self,
        epic_id: str,
        status: str,
        updated_at: str,
    ) -> None:
        """Synchronous Epic status update."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.UPDATE_EPIC_STATUS.value,
                epic_id=epic_id,
                status=status,
                updated_at=updated_at,
            )
            return result.single() is not None

        with self._session() as session:
            found = self._retry_operation(session.execute_write, _tx)

        if not found:
            logger.warning(f"Epic node not found in graph for update: {epic_id}")

    async def get_epic_ids_by_project(self, project_id: str) -> list[str]:
        """
        Get all Epic IDs for a project.

        Args:
            project_id: Project ID.

        Returns:
            List of Epic IDs.
        """
        return await asyncio.to_thread(
            self._get_epic_ids_by_project_sync,
            project_id,
        )

    def _get_epic_ids_by_project_sync(self, project_id: str) -> list[str]:
        """Synchronous query for Epic IDs."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_EPIC_IDS_BY_PROJECT.value,
                project_id=project_id,
            )
            return [record["epic_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

