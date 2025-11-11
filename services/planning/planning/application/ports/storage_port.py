"""Storage port for Planning Service (dual persistence: Neo4j + Valkey)."""

from typing import Protocol

from planning.domain import Story, StoryId, StoryList, StoryState
from planning.domain.entities.epic import Epic
from planning.domain.entities.plan import Plan
from planning.domain.entities.project import Project
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId


class StoragePort(Protocol):
    """
    Port (interface) for persistence (Project, Epic, Story).

    Dual Persistence Strategy:
    - Neo4j: Graph relationships, historical data, complex queries
    - Valkey: Current state, FSM cache, fast reads

    Hierarchy support: Project → Epic → Story → Task

    Implementations will handle coordination between both stores.
    """

    # ========== Project Methods (Root of Hierarchy) ==========

    async def save_project(self, project: Project) -> None:
        """Persist a project to both Neo4j and Valkey.

        Args:
            project: Project to persist

        Raises:
            StorageError: If persistence fails
        """
        ...

    async def get_project(self, project_id: ProjectId) -> Project | None:
        """Retrieve a project by ID.

        Args:
            project_id: ID of project to retrieve

        Returns:
            Project if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        ...

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List all projects.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Project entities

        Raises:
            StorageError: If query fails
        """
        ...

    # ========== Epic Methods (Groups Stories) ==========

    async def save_epic(self, epic: Epic) -> None:
        """Persist an epic to both Neo4j and Valkey.

        Domain Invariant: Epic MUST have project_id.

        Args:
            epic: Epic to persist

        Raises:
            ValueError: If epic.project_id is empty
            StorageError: If persistence fails
        """
        ...

    async def get_epic(self, epic_id: EpicId) -> Epic | None:
        """Retrieve an epic by ID.

        Args:
            epic_id: ID of epic to retrieve

        Returns:
            Epic if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        ...

    async def list_epics(
        self,
        project_id: ProjectId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Epic]:
        """List epics, optionally filtered by project.

        Args:
            project_id: Optional filter by project
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Epic entities

        Raises:
            StorageError: If query fails
        """
        ...

    # ========== Story Methods ==========

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
    ) -> StoryList:
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
            StoryList collection matching criteria.

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

    # ========== Task Methods ==========

    async def save_task(self, task: Task) -> None:
        """Persist a task to both Neo4j and Valkey.

        Domain Invariant: Task MUST have story_id.

        Args:
            task: Task to persist

        Raises:
            ValueError: If task.story_id is empty
            StorageError: If persistence fails
        """
        ...

    async def get_task(self, task_id: TaskId) -> Task | None:
        """Retrieve a task by ID.

        Args:
            task_id: ID of task to retrieve

        Returns:
            Task if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        ...

    async def list_tasks(
        self,
        story_id: StoryId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks, optionally filtered by story.

        Args:
            story_id: Optional filter by story
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Task entities

        Raises:
            StorageError: If query fails
        """
        ...
    
    # ========== Plan Methods ==========
    
    async def save_plan(self, plan: Plan) -> None:
        """Persist a plan to both Neo4j and Valkey.
        
        Domain Invariant: Plan MUST have story_id.
        
        Args:
            plan: Plan to persist
            
        Raises:
            ValueError: If plan.story_id is empty
            StorageError: If persistence fails
        """
        ...
    
    async def get_plan(self, plan_id: PlanId) -> Plan | None:
        """Retrieve a plan by ID.
        
        Args:
            plan_id: ID of plan to retrieve
            
        Returns:
            Plan if found, None otherwise
            
        Raises:
            StorageError: If retrieval fails
        """
        ...

