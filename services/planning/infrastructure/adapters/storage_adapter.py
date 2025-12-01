"""Composite storage adapter coordinating Neo4j (graph) + Valkey (details)."""

import logging

from planning.application.ports import StoragePort
from planning.domain import Story, StoryId, StoryList, StoryState
from planning.domain.entities.epic import Epic
from planning.domain.entities.project import Project
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig
from planning.infrastructure.adapters.valkey_adapter import ValkeyConfig, ValkeyStorageAdapter
from planning.infrastructure.mappers.epic_neo4j_mapper import EpicNeo4jMapper
from planning.infrastructure.mappers.project_neo4j_mapper import ProjectNeo4jMapper

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
            created_by=story.created_by.value,  # Extract string value from UserName Value Object
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
        epic_id: EpicId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> StoryList:
        """
        List stories from Valkey.

        Uses Valkey sets for efficient filtering by state.

        Args:
            state_filter: Filter by state (optional).
            epic_id: Filter by epic (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            StoryList collection.
        """
        return await self.valkey.list_stories(
            state_filter=state_filter,
            epic_id=epic_id,
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

    async def save_task(self, task: Task) -> None:
        """
        Persist task to Neo4j (graph) + Valkey (details).

        Operations:
        1. Save full details to Valkey
        2. Create graph node in Neo4j (minimal properties)
        3. Create Story→Task relationship (REQUIRED - domain invariant)
        4. Create PlanVersion→Task relationship (OPTIONAL, only if plan_id exists)

        Args:
            task: Task to persist.

        Raises:
            ValueError: If task.story_id is empty (domain invariant violation)
            Exception: If persistence fails.
        """
        if not task.story_id:
            raise ValueError("Task story_id is required (domain invariant)")

        # 1. Save details to Valkey (permanent storage)
        await self.valkey.save_task(task)

        # 2. Create graph node in Neo4j (structure only)
        # Create Story→Task relationship (REQUIRED)
        # Create PlanVersion→Task relationship (OPTIONAL)
        await self.neo4j.create_task_node(
            task_id=task.task_id,
            story_id=task.story_id,
            status=task.status,
            task_type=task.type,
            plan_id=task.plan_id,  # Optional
        )

        logger.info(f"Task saved (dual): {task.task_id} (story: {task.story_id})")

    async def get_task(self, task_id: TaskId) -> Task | None:
        """
        Retrieve task from Valkey.

        Note: Valkey has all details, Neo4j only has graph structure.

        Args:
            task_id: ID of task to retrieve.

        Returns:
            Task if found, None otherwise.
        """
        return await self.valkey.get_task(task_id)

    async def list_tasks(
        self,
        story_id: StoryId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """
        List tasks, optionally filtered by story.

        Args:
            story_id: Optional filter by story.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of Task entities.
        """
        return await self.valkey.list_tasks(
            story_id=story_id,
            limit=limit,
            offset=offset,
        )

    async def save_task_dependencies(
        self,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        """
        Persist task dependency relationships to Neo4j.

        Creates DEPENDS_ON relationships between tasks in Neo4j graph.
        Each dependency includes the reason for the dependency.

        Args:
            dependencies: Tuple of dependency edges to persist

        Raises:
            StorageError: If persistence fails
        """
        await self.neo4j.create_task_dependencies(dependencies)
        logger.info(f"Task dependencies persisted: {len(dependencies)} relationships")

    async def save_project(self, project: Project) -> None:
        """
        Persist project to Neo4j (graph) + Valkey (details).

        Operations:
        1. Save full details to Valkey
        2. Create graph node in Neo4j (minimal properties)

        Args:
            project: Project to persist.

        Raises:
            Exception: If persistence fails.
        """
        # 1. Save details to Valkey (permanent storage)
        await self.valkey.save_project(project)

        # 2. Create graph node in Neo4j (structure only)
        props = ProjectNeo4jMapper.to_graph_properties(project)
        await self.neo4j.create_project_node(
            project_id=props["id"],
            name=props["name"],
            status=props["status"],
            created_at=props["created_at"],
            updated_at=props["updated_at"],
        )

        logger.info(f"Project saved (dual): {project.project_id}")

    async def get_project(self, project_id: ProjectId) -> Project | None:
        """
        Retrieve project from Valkey.

        Note: Valkey has all details.

        Args:
            project_id: ID of project to retrieve.

        Returns:
            Project if found, None otherwise.
        """
        return await self.valkey.get_project(project_id)

    async def list_projects(
        self,
        status_filter: ProjectStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """
        List all projects with optional status filtering and pagination.

        Uses Valkey sets for efficient listing and filtering.

        Args:
            status_filter: Filter by status (optional)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Project entities (empty list if no projects found)

        Raises:
            StorageError: If query fails
        """
        return await self.valkey.list_projects(
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )

    # ========== Epic Methods ==========

    async def save_epic(self, epic: Epic) -> None:
        """
        Persist epic to Neo4j (graph) + Valkey (details).

        Operations:
        1. Save full details to Valkey
        2. Create graph node in Neo4j (minimal properties)

        Args:
            epic: Epic to persist.

        Raises:
            Exception: If persistence fails.
        """
        # 1. Save details to Valkey (permanent storage)
        await self.valkey.save_epic(epic)

        # 2. Create graph node in Neo4j (structure only)
        props = EpicNeo4jMapper.to_graph_properties(epic)
        await self.neo4j.create_epic_node(
            epic_id=props["id"],
            project_id=props["project_id"],
            name=props["name"],
            status=props["status"],
            created_at=props["created_at"],
            updated_at=props["updated_at"],
        )

        logger.info(f"Epic saved (dual): {epic.epic_id}")

    async def get_epic(self, epic_id: EpicId) -> Epic | None:
        """
        Retrieve epic from Valkey.

        Note: Valkey has all details.

        Args:
            epic_id: ID of epic to retrieve.

        Returns:
            Epic if found, None otherwise.
        """
        return await self.valkey.get_epic(epic_id)

    async def list_epics(
        self,
        project_id: ProjectId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Epic]:
        """
        List epics with optional project filtering and pagination.

        Uses Valkey sets for efficient listing and filtering.

        Args:
            project_id: Filter by project (optional)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Epic entities (empty list if no epics found)

        Raises:
            StorageError: If query fails
        """
        return await self.valkey.list_epics(
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

