"""Neo4j adapter for Planning Service - Graph structure only."""

import asyncio
import logging

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
from planning.domain import StoryId, StoryState, Title
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
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
        epic_id: EpicId,
        title: Title,
        created_by: str,
        initial_state: StoryState,
    ) -> None:
        """
        Create Story node in graph with minimal properties.

        Creates:
        - Story node with id, title, and current state
        - User node if doesn't exist
        - CREATED_BY relationship
        - BELONGS_TO relationship with Epic (domain invariant)

        Args:
            story_id: Story ID.
            epic_id: Epic ID (parent Epic - REQUIRED domain invariant).
            title: Story title (Value Object).
            created_by: User who created the story.
            initial_state: Initial FSM state.
        """
        await asyncio.to_thread(
            self._create_story_node_sync,
            story_id,
            epic_id,
            title,
            created_by,
            initial_state,
        )
        logger.info(f"Story node created in graph: {story_id} (belongs to Epic: {epic_id})")

    def _create_story_node_sync(
        self,
        story_id: StoryId,
        epic_id: EpicId,
        title: Title,
        created_by: str,
        initial_state: StoryState,
    ) -> None:
        """Synchronous node creation."""
        def _tx(tx):
            tx.run(
                Neo4jQuery.CREATE_STORY_NODE.value,
                story_id=story_id.value,
                epic_id=epic_id.value,  # Extract string value from EpicId Value Object
                title=title.value,  # Extract string value from Title Value Object
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
            name: Project name (also used as title for graph queries).
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
            name: Epic title/name (also used as title for graph queries).
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
                title=name,  # Use name (which comes from epic.title) as title for graph queries (required by GetGraphRelationships)
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

    # ========== Task Methods ==========

    async def create_task_node(
        self,
        task_id: TaskId,
        story_id: StoryId,
        status: TaskStatus,
        task_type: TaskType,
        plan_id: PlanId | None = None,
    ) -> None:
        """
        Create Task node in graph and link to Story (and optionally Plan).

        Creates:
        - Task node with id, status, type
        - Story→Task relationship (REQUIRED - domain invariant)
        - Plan→Task relationship (OPTIONAL, only if plan_id provided)

        Args:
            task_id: Task ID.
            story_id: Parent Story ID (REQUIRED - domain invariant).
            status: Task status.
            task_type: Task type.
            plan_id: Optional parent Plan ID.
        """
        await asyncio.to_thread(
            self._create_task_node_sync,
            task_id,
            story_id,
            status,
            task_type,
            plan_id,
        )
        logger.info(
            f"Task node created in graph: {task_id} (Story: {story_id}, Plan: {plan_id})"
        )

    def _create_task_node_sync(
        self,
        task_id: TaskId,
        story_id: StoryId,
        status: TaskStatus,
        task_type: TaskType,
        plan_id: PlanId | None,
    ) -> None:
        """Synchronous Task node creation."""
        def _tx(tx):
            # Create task node and link to story (REQUIRED)
            tx.run(
                Neo4jQuery.CREATE_TASK_NODE.value,
                task_id=task_id.value,
                story_id=story_id.value,
                status=str(status),  # TaskStatus enum string value
                type=str(task_type),  # TaskType enum string value
            )

            # Link to plan if provided (OPTIONAL)
            if plan_id:
                tx.run(
                    Neo4jQuery.CREATE_TASK_PLAN_RELATIONSHIP.value,
                    task_id=task_id.value,
                    plan_id=plan_id.value,
                )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def create_task_node_with_semantic_relationship(
        self,
        task_id: TaskId,
        story_id: StoryId,
        plan_id: PlanId,
        status: TaskStatus,
        task_type: TaskType,
        priority: int,
        decision_metadata: dict[str, str],
    ) -> None:
        """
        Create Task node with SEMANTIC HAS_TASK relationship.

        This method creates the task node and establishes a relationship
        with rich semantic metadata explaining WHY this task exists.

        Creates:
        - Task node with id, status, type, priority
        - Story→Task relationship (CONTAINS)
        - Plan→Task relationship (HAS_TASK) WITH semantic properties:
          * decided_by: Who decided (ARCHITECT, QA, DEVOPS, PO)
          * decision_reason: WHY this task is needed
          * council_feedback: Full context from council
          * source: Origin (BACKLOG_REVIEW, PLANNING_MEETING)
          * decided_at: ISO 8601 timestamp
          * task_index: Order in plan

        Enables:
        - Context rehydration with decision history
        - Observability (WHO decided, WHY, WHEN)
        - Post-mortem analysis
        - Knowledge graph queries

        Args:
            task_id: Task ID
            story_id: Parent Story ID (REQUIRED)
            plan_id: Parent Plan ID (REQUIRED)
            status: Task status
            task_type: Task type
            priority: Task priority
            decision_metadata: Dict with semantic context:
                - decided_by (str): Council/actor
                - decision_reason (str): Why task exists
                - council_feedback (str): Full context
                - source (str): Origin
                - decided_at (str): ISO timestamp
        """
        await asyncio.to_thread(
            self._create_task_node_with_semantic_relationship_sync,
            task_id,
            story_id,
            plan_id,
            status,
            task_type,
            priority,
            decision_metadata,
        )
        logger.info(
            f"Task node created with semantic relationship: {task_id} "
            f"(Story: {story_id}, Plan: {plan_id}, decided_by: {decision_metadata['decided_by']})"
        )

    def _create_task_node_with_semantic_relationship_sync(
        self,
        task_id: TaskId,
        story_id: StoryId,
        plan_id: PlanId,
        status: TaskStatus,
        task_type: TaskType,
        priority: int,
        decision_metadata: dict[str, str],
    ) -> None:
        """Synchronous Task node creation with semantic relationship."""
        def _tx(tx):
            # Query to create task and semantic relationships
            query = """
                // Match parent nodes
                MATCH (s:Story {id: $story_id})
                MATCH (p:Plan {id: $plan_id})

                // Create Task node
                CREATE (t:Task {
                    id: $task_id,
                    status: $status,
                    type: $type,
                    priority: $priority
                })

                // Create Story→Task relationship (containment)
                CREATE (s)-[:CONTAINS]->(t)

                // Create Plan→Task relationship WITH semantic metadata
                CREATE (p)-[:HAS_TASK {
                    decided_by: $decided_by,
                    decision_reason: $decision_reason,
                    council_feedback: $council_feedback,
                    source: $source,
                    decided_at: $decided_at,
                    task_index: $task_index
                }]->(t)

                RETURN t
            """

            tx.run(
                query,
                task_id=task_id.value,
                story_id=story_id.value,
                plan_id=plan_id.value,
                status=str(status),
                type=str(task_type),
                priority=priority,
                decided_by=decision_metadata["decided_by"],
                decision_reason=decision_metadata["decision_reason"],
                council_feedback=decision_metadata["council_feedback"],
                source=decision_metadata["source"],
                decided_at=decision_metadata["decided_at"],
                task_index=decision_metadata.get("task_index", 0),
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def get_task_ids_by_story(self, story_id: StoryId) -> list[str]:
        """
        Get all Task IDs for a story.

        Args:
            story_id: Story ID.

        Returns:
            List of Task IDs.
        """
        return await asyncio.to_thread(
            self._get_task_ids_by_story_sync,
            story_id,
        )

    def _get_task_ids_by_story_sync(self, story_id: StoryId) -> list[str]:
        """Synchronous query for Task IDs by story."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_TASK_IDS_BY_STORY.value,
                story_id=story_id.value,
            )
            return [record["task_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

    async def get_task_ids_by_plan(self, plan_id: PlanId) -> list[str]:
        """
        Get all Task IDs for a plan.

        Args:
            plan_id: Plan ID.

        Returns:
            List of Task IDs.
        """
        return await asyncio.to_thread(
            self._get_task_ids_by_plan_sync,
            plan_id,
        )

    def _get_task_ids_by_plan_sync(self, plan_id: PlanId) -> list[str]:
        """Synchronous query for Task IDs by plan."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_TASK_IDS_BY_PLAN.value,
                plan_id=plan_id.value,
            )
            return [record["task_id"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

    # ========== Backlog Review Ceremony Methods ==========

    async def save_backlog_review_ceremony_node(
        self,
        ceremony_id: str,
        properties: dict,
        story_ids: list[str],
        project_id: str | None = None,
    ) -> None:
        """
        Create or update BacklogReviewCeremony node and link to Stories and Project.

        Args:
            ceremony_id: Ceremony ID.
            properties: Ceremony properties dict.
            story_ids: List of Story IDs to link.
            project_id: Project ID to link (optional, inferred from stories if not provided).
        """
        await asyncio.to_thread(
            self._save_backlog_review_ceremony_node_sync,
            ceremony_id,
            properties,
            story_ids,
            project_id,
        )
        logger.info(f"BacklogReviewCeremony node saved: {ceremony_id}")

    def _save_backlog_review_ceremony_node_sync(
        self,
        ceremony_id: str,
        properties: dict,
        story_ids: list[str],
        project_id: str | None = None,
    ) -> None:
        """Synchronous ceremony node save."""
        def _tx(tx):
            # Create or update ceremony node
            tx.run(
                Neo4jQuery.CREATE_CEREMONY_NODE.value,
                ceremony_id=ceremony_id,
                created_by=properties.get("created_by"),
                status=properties.get("status"),
                created_at=properties.get("created_at"),
                updated_at=properties.get("updated_at"),
                started_at=properties.get("started_at"),
                completed_at=properties.get("completed_at"),
                story_count=properties.get("story_count", len(story_ids)),
                review_results_json=properties.get("review_results_json", "[]"),
            )

            # Link ceremony to project if provided
            if project_id:
                tx.run(
                    Neo4jQuery.CREATE_CEREMONY_PROJECT_RELATIONSHIP.value,
                    ceremony_id=ceremony_id,
                    project_id=project_id,
                )

            # Create relationships to stories
            for story_id in story_ids:
                tx.run(
                    Neo4jQuery.CREATE_CEREMONY_STORY_RELATIONSHIP.value,
                    ceremony_id=ceremony_id,
                    story_id=story_id,
                )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def get_backlog_review_ceremony_node(
        self,
        ceremony_id: str,
    ) -> dict | None:
        """
        Get BacklogReviewCeremony node with properties and story IDs.

        Args:
            ceremony_id: Ceremony ID.

        Returns:
            Dict with 'properties', 'story_ids', and 'review_results_json' keys,
            or None if not found.
        """
        return await asyncio.to_thread(
            self._get_backlog_review_ceremony_node_sync,
            ceremony_id,
        )

    def _get_backlog_review_ceremony_node_sync(
        self,
        ceremony_id: str,
    ) -> dict | None:
        """Synchronous ceremony node retrieval."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.GET_CEREMONY_NODE.value,
                ceremony_id=ceremony_id,
            )
            record = result.single()
            if record:
                return record["result"]
            return None

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

    async def list_backlog_review_ceremony_nodes(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        List BacklogReviewCeremony nodes with pagination.

        Args:
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of dicts with 'properties', 'story_ids', and 'review_results_json' keys.
        """
        return await asyncio.to_thread(
            self._list_backlog_review_ceremony_nodes_sync,
            limit,
            offset,
        )

    def _list_backlog_review_ceremony_nodes_sync(
        self,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Synchronous ceremony nodes listing."""
        def _tx(tx):
            result = tx.run(
                Neo4jQuery.LIST_CEREMONY_NODES.value,
                limit=limit,
                offset=offset,
            )
            return [record["result"] for record in result]

        with self._session() as session:
            return self._retry_operation(session.execute_read, _tx)

