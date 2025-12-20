"""Storage port for Planning Service (dual persistence: Neo4j + Valkey)."""

from typing import Protocol

from planning.domain.entities.story import Story
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.collections.story_list import StoryList
from planning.domain.value_objects.statuses.story_state import StoryState
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.epic import Epic
from planning.domain.entities.plan import Plan
from planning.domain.entities.project import Project
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge


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

    async def list_projects(
        self,
        status_filter: ProjectStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """List all projects with optional status filtering.

        Args:
            status_filter: Filter by status (optional)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Project entities

        Raises:
            StorageError: If query fails
        """
        ...

    async def delete_project(self, project_id: ProjectId) -> None:
        """Delete a project from both Neo4j and Valkey.

        Neo4j:
        - Delete node and all relationships (cascades to epics, stories, tasks)

        Valkey:
        - Remove from cache and all sets

        Args:
            project_id: ID of project to delete.

        Raises:
            StorageError: If deletion fails.
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

    async def delete_epic(self, epic_id: EpicId) -> None:
        """Delete an epic from both Neo4j and Valkey.

        Neo4j:
        - Delete node and all relationships (cascades to stories, tasks)

        Valkey:
        - Remove from cache and all sets

        Args:
            epic_id: ID of epic to delete.

        Raises:
            StorageError: If deletion fails.
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
        epic_id: EpicId | None = None,
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
            epic_id: Filter by epic (optional).
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

    async def save_task_with_decision(
        self,
        task: Task,
        decision_metadata: dict[str, str],
    ) -> None:
        """Persist a task with semantic decision metadata to Neo4j + Valkey.

        Creates task node and HAS_TASK relationship with decision properties:
        - decided_by: Who decided (ARCHITECT, QA, DEVOPS, PO)
        - decision_reason: WHY this task is needed (semantic context)
        - council_feedback: Full feedback from council
        - source: Origin (BACKLOG_REVIEW, PLANNING_MEETING, PO_REQUEST)
        - decided_at: ISO 8601 timestamp

        This enables:
        - Context rehydration with decision history
        - Observability and auditing
        - Post-mortem analysis
        - Knowledge graph queries

        Args:
            task: Task to persist
            decision_metadata: Dict with decision context:
                - decided_by (str): Council or actor
                - decision_reason (str): Why task exists
                - council_feedback (str): Full context
                - source (str): Origin of task
                - decided_at (str): ISO timestamp

        Raises:
            ValueError: If task.story_id is empty or required metadata missing
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

    # ========== Task Dependency Methods ==========

    async def save_task_with_deliberations(
        self,
        task: Task,
        deliberation_indices: list[int],
        ceremony_id: BacklogReviewCeremonyId,
    ) -> None:
        """Persist a task with associated agent deliberations to Neo4j + Valkey.

        Creates task node and stores relationship to agent deliberations.
        This enables:
        - Observability: See which agent deliberations contributed to each task
        - Rehydration: Reconstruct context from deliberations
        - Traceability: Track decision history

        Args:
            task: Task to persist
            deliberation_indices: List of indices into ceremony's agent_deliberations
            ceremony_id: Ceremony identifier (for retrieving deliberations)
        """
        pass

    async def save_task_dependencies(
        self,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        """Persist task dependency relationships to Neo4j.

        Creates DEPENDS_ON relationships between tasks in Neo4j graph.
        Each dependency includes the reason for the dependency.

        Args:
            dependencies: Tuple of dependency edges to persist

        Raises:
            StorageError: If persistence fails
        """
        ...

    # ========== Backlog Review Ceremony Methods ==========

    async def save_backlog_review_ceremony(self, ceremony: BacklogReviewCeremony) -> None:
        """Persist a backlog review ceremony to Neo4j only.

        Note: Ceremonies are stored only in Neo4j (not in Valkey).
        Unlike Stories/Tasks which need detailed content in Valkey for context rehydration,
        ceremonies have all their data in Neo4j.

        Neo4j:
        - Store ceremony node with all attributes
        - Create REVIEWS relationships to stories
        - Create BELONGS_TO relationship to project

        Args:
            ceremony: BacklogReviewCeremony to persist

        Raises:
            StorageError: If persistence fails
        """
        ...

    async def get_backlog_review_ceremony(
        self,
        ceremony_id: BacklogReviewCeremonyId,
    ) -> BacklogReviewCeremony | None:
        """Retrieve a backlog review ceremony by ID from Neo4j.

        Note: Ceremonies are stored only in Neo4j (not in Valkey).
        Unlike Stories/Tasks which need detailed content in Valkey for context rehydration,
        ceremonies have all their data in Neo4j.

        Strategy:
        - Query Neo4j directly (ceremonies are stored only in Neo4j)

        Args:
            ceremony_id: ID of ceremony to retrieve

        Returns:
            BacklogReviewCeremony if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        ...

    async def list_backlog_review_ceremonies(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BacklogReviewCeremony]:
        """List backlog review ceremonies.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of BacklogReviewCeremony entities

        Raises:
            StorageError: If query fails
        """
        ...

