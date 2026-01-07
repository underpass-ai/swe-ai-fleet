"""Valkey (Redis-compatible) adapter for Planning Service - Permanent Storage."""

import asyncio
import json
import logging

import valkey  # Valkey is Redis-compatible
from planning.application.ports import StoragePort
from planning.domain import Story, StoryId, StoryList, StoryState, StoryStateEnum
from planning.domain.entities.epic import Epic
from planning.domain.entities.project import Project
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.review.po_concerns import PoConcerns
from planning.domain.value_objects.review.po_notes import PoNotes
from planning.domain.value_objects.review.story_po_approval import StoryPoApproval
from planning.domain.value_objects.statuses.priority_adjustment import (
    PriorityAdjustment,
)
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys
from planning.infrastructure.mappers.epic_valkey_mapper import EpicValkeyMapper
from planning.infrastructure.mappers.project_valkey_mapper import ProjectValkeyMapper
from planning.infrastructure.mappers.story_valkey_fields import StoryValkeyFields
from planning.infrastructure.mappers.story_valkey_mapper import StoryValkeyMapper
from planning.infrastructure.mappers.task_valkey_mapper import TaskValkeyMapper

logger = logging.getLogger(__name__)


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

        # Create Valkey client (Redis-compatible)
        self.client = valkey.Valkey(
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

    async def set_json(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        """
        Store JSON data in Valkey.

        Args:
            key: Redis key
            value: Dictionary to store as JSON
            ttl_seconds: Optional TTL in seconds
        """
        json_str = json.dumps(value)
        await asyncio.to_thread(self.client.set, key, json_str, ex=ttl_seconds if ttl_seconds else None)

    async def get_json(self, key: str) -> dict | None:
        """
        Retrieve JSON data from Valkey.

        Args:
            key: Redis key

        Returns:
            Dictionary if found, None otherwise
        """
        json_str = await asyncio.to_thread(self.client.get, key)
        if json_str is None:
            return None
        return json.loads(json_str)

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

    def _stories_by_epic_set_key(self, epic_id: EpicId) -> str:
        """Key for set containing story IDs by epic."""
        return ValkeyKeys.stories_by_epic(epic_id)

    async def save_story(self, story: Story) -> None:
        """
        Persist story details to Valkey (permanent storage).

        Stores:
        - Hash with all story fields (permanent, no TTL)
        - FSM state string for fast lookups
        - Story ID in sets for indexing (all, state, epic)

        Args:
            story: Story to persist.
        """
        # Get old epic_id to update sets if needed
        hash_key = self._story_hash_key(story.story_id)
        old_epic_id_str = self.client.hget(hash_key, StoryValkeyFields.EPIC_ID)

        # Store story as hash (all fields) using mapper
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

        # Handle Epic set update
        if old_epic_id_str and old_epic_id_str != story.epic_id.value:
            # Remove from old epic set
            old_epic_key = self._stories_by_epic_set_key(EpicId(old_epic_id_str))
            self.client.srem(old_epic_key, story.story_id.value)

        # Add to new epic set (or ensure it's in current epic set)
        epic_key = self._stories_by_epic_set_key(story.epic_id)
        self.client.sadd(epic_key, story.story_id.value)

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
        epic_id: EpicId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> StoryList:
        """
        List stories from Valkey with optional filtering.

        Args:
            state_filter: Filter by state (optional).
            epic_id: Filter by epic (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            StoryList collection.
        """
        return await asyncio.to_thread(
            self._list_stories_sync,
            state_filter,
            epic_id,
            limit,
            offset,
        )

    def _list_stories_sync(
        self,
        state_filter: StoryState | None,
        epic_id: EpicId | None,
        limit: int,
        offset: int,
    ) -> StoryList:
        """Synchronous list_stories for thread execution."""
        # Get story IDs (filtered or all)
        # smembers() returns set[str] for synchronous Redis client
        story_ids_set: set[str]

        # Start with all stories or filter by one criteria
        if state_filter:
            story_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._stories_by_state_set_key(state_filter)
            )
        elif epic_id:
            story_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._stories_by_epic_set_key(epic_id)
            )
        else:
            story_ids_set = self.client.smembers(self._all_stories_set_key())  # type: ignore[assignment]

        # Apply intersection if multiple filters
        if state_filter and epic_id:
             epic_ids_set = self.client.smembers(
                 self._stories_by_epic_set_key(epic_id)
             )
             story_ids_set = story_ids_set.intersection(epic_ids_set) # type: ignore[arg-type]

        story_ids = list(story_ids_set)

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
        - Epic-specific sets (if epic changed)

        Args:
            story: Updated story.
        """
        # Get old state and epic to update sets if needed
        hash_key = self._story_hash_key(story.story_id)
        old_data = self.client.hmget(hash_key, [StoryValkeyFields.STATE, StoryValkeyFields.EPIC_ID])
        old_state_str = old_data[0]
        old_epic_id_str = old_data[1]

        # Update hash using mapper
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

        # If epic changed, update epic sets
        if old_epic_id_str and old_epic_id_str != story.epic_id.value:
            # Remove from old epic set
            self.client.srem(
                self._stories_by_epic_set_key(EpicId(old_epic_id_str)),
                story.story_id.value,
            )

            # Add to new epic set
            self.client.sadd(
                self._stories_by_epic_set_key(story.epic_id),
                story.story_id.value,
            )

        logger.info(f"Story updated in Valkey: {story.story_id}")

    async def delete_story(self, story_id: StoryId) -> None:
        """
        Delete story from Valkey permanent storage.

        Deletes:
        - Hash with all fields
        - FSM state string
        - Story ID from sets (all, state, epic)

        Args:
            story_id: ID of story to delete.
        """
        # Get current state and epic to remove from sets
        hash_key = self._story_hash_key(story_id)
        old_data = self.client.hmget(hash_key, [StoryValkeyFields.STATE, StoryValkeyFields.EPIC_ID])
        state_str = old_data[0]
        epic_id_str = old_data[1]

        # Delete hash
        self.client.delete(hash_key)

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

        # Remove from epic-specific set
        if epic_id_str:
            self.client.srem(
                self._stories_by_epic_set_key(EpicId(epic_id_str)),
                story_id.value,
            )

        logger.info(f"Story deleted from Valkey: {story_id}")

    # ========== Project Methods ==========

    def _project_hash_key(self, project_id: ProjectId) -> str:
        """Generate hash key for project details."""
        return ValkeyKeys.project_hash(project_id)

    def _all_projects_set_key(self) -> str:
        """Key for set containing all project IDs."""
        return ValkeyKeys.all_projects()

    def _projects_by_status_key(self, status: str) -> str:
        """Key for set containing project IDs by status."""
        return ValkeyKeys.projects_by_status(status)

    async def save_project(self, project: Project) -> None:
        """
        Persist project details to Valkey (permanent storage).

        Stores:
        - Hash with all project fields (permanent, no TTL)
        - Project ID in set for indexing
        - Project ID in status-specific set for filtering

        Handles status changes by updating sets if status changed.

        Args:
            project: Project to persist.

        Raises:
            Exception: If persistence fails.
        """
        # Get old status to update sets if needed
        hash_key = self._project_hash_key(project.project_id)
        old_status_str = self.client.hget(hash_key, "status")

        # Store project as hash (all fields) using mapper
        project_data = ProjectValkeyMapper.to_dict(project)
        self.client.hset(hash_key, mapping=project_data)

        # Add to all projects set
        self.client.sadd(self._all_projects_set_key(), project.project_id.value)

        # If status changed, update status sets
        if old_status_str and old_status_str != project.status.value:
            # Remove from old status set
            old_status_key = self._projects_by_status_key(old_status_str)
            self.client.srem(old_status_key, project.project_id.value)

        # Add to new status set (or ensure it's in current status set)
        status_key = self._projects_by_status_key(project.status.value)
        self.client.sadd(status_key, project.project_id.value)

        logger.info(f"Project saved to Valkey: {project.project_id}")

    async def get_project(self, project_id: ProjectId) -> Project | None:
        """
        Retrieve project from Valkey permanent storage.

        Args:
            project_id: ID of project to retrieve.

        Returns:
            Project if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_project_sync, project_id)

    def _get_project_sync(self, project_id: ProjectId) -> Project | None:
        """Synchronous get_project for thread execution."""
        hash_key = self._project_hash_key(project_id)
        data = self.client.hgetall(hash_key)

        if not data:
            logger.debug(f"Project not found in Valkey: {project_id}")
            return None

        logger.debug(f"Project retrieved from Valkey: {project_id}")

        # Convert hash to Project entity using mapper
        return ProjectValkeyMapper.from_dict(data)

    async def list_projects(
        self,
        status_filter: ProjectStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """
        List projects from Valkey with optional status filtering and pagination.

        Args:
            status_filter: Filter by status (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of Project entities.
        """
        return await asyncio.to_thread(
            self._list_projects_sync,
            status_filter,
            limit,
            offset,
        )

    def _list_projects_sync(
        self,
        status_filter: ProjectStatus | None,
        limit: int,
        offset: int,
    ) -> list[Project]:
        """Synchronous list_projects for thread execution."""
        # Get project IDs (filtered or all)
        # smembers() returns set[str] for synchronous Redis client
        project_ids_set: set[str]
        if status_filter:
            project_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._projects_by_status_key(status_filter.value)
            )
        else:
            project_ids_set = self.client.smembers(self._all_projects_set_key())  # type: ignore[assignment]

        project_ids = list(project_ids_set)

        # Sort by ID (creation order approximation)
        project_ids.sort()

        # Apply pagination
        paginated_ids = project_ids[offset : offset + limit]

        # Retrieve full projects synchronously
        projects = []
        for project_id_str in paginated_ids:
            project = self._get_project_sync(ProjectId(project_id_str))
            if project:
                projects.append(project)

        return projects

    async def delete_project(self, project_id: ProjectId) -> None:
        """
        Delete project from Valkey permanent storage.

        Deletes:
        - Hash with all fields
        - Project ID from sets (all, status)

        Args:
            project_id: ID of project to delete.
        """
        # Get current status to remove from sets
        hash_key = self._project_hash_key(project_id)
        status_str = self.client.hget(hash_key, "status")

        # Delete hash
        self.client.delete(hash_key)

        # Remove from all projects set
        self.client.srem(self._all_projects_set_key(), project_id.value)

        # Remove from status-specific set
        if status_str:
            self.client.srem(
                self._projects_by_status_key(status_str),
                project_id.value,
            )

        logger.info(f"Project deleted from Valkey: {project_id}")

    # ========== Epic Methods ==========

    def _epic_hash_key(self, epic_id: EpicId) -> str:
        """Generate hash key for epic details."""
        return ValkeyKeys.epic_hash(epic_id)

    def _all_epics_set_key(self) -> str:
        """Key for set containing all epic IDs."""
        return ValkeyKeys.all_epics()

    def _epics_by_project_key(self, project_id: ProjectId) -> str:
        """Key for set containing epic IDs by project."""
        return ValkeyKeys.epics_by_project(project_id)

    async def save_epic(self, epic: Epic) -> None:
        """
        Persist epic details to Valkey (permanent storage).

        Stores:
        - Hash with all epic fields (permanent, no TTL)
        - Epic ID in set for indexing
        - Epic ID in project-specific set for filtering

        Args:
            epic: Epic to persist.

        Raises:
            Exception: If persistence fails.
        """
        # Get old project_id to update sets if needed
        hash_key = self._epic_hash_key(epic.epic_id)
        old_project_id_str = self.client.hget(hash_key, "project_id")

        # Store epic as hash (all fields) using mapper
        epic_data = EpicValkeyMapper.to_dict(epic)
        self.client.hset(hash_key, mapping=epic_data)

        # Add to all epics set
        self.client.sadd(self._all_epics_set_key(), epic.epic_id.value)

        # If project_id changed, update project sets
        if old_project_id_str and old_project_id_str != epic.project_id.value:
            # Remove from old project set
            old_project_key = self._epics_by_project_key(ProjectId(old_project_id_str))
            self.client.srem(old_project_key, epic.epic_id.value)

        # Add to new project set (or ensure it's in current project set)
        project_key = self._epics_by_project_key(epic.project_id)
        self.client.sadd(project_key, epic.epic_id.value)

        logger.info(f"Epic saved to Valkey: {epic.epic_id}")

    async def get_epic(self, epic_id: EpicId) -> Epic | None:
        """
        Retrieve epic from Valkey permanent storage.

        Args:
            epic_id: ID of epic to retrieve.

        Returns:
            Epic if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_epic_sync, epic_id)

    def _get_epic_sync(self, epic_id: EpicId) -> Epic | None:
        """Synchronous get_epic for thread execution."""
        hash_key = self._epic_hash_key(epic_id)
        data = self.client.hgetall(hash_key)

        if not data:
            logger.debug(f"Epic not found in Valkey: {epic_id}")
            return None

        logger.debug(f"Epic retrieved from Valkey: {epic_id}")

        # Convert hash to Epic entity using mapper
        return EpicValkeyMapper.from_dict(data)

    async def list_epics(
        self,
        project_id: ProjectId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Epic]:
        """
        List epics from Valkey with optional project filtering and pagination.

        Args:
            project_id: Filter by project (optional).
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of Epic entities.
        """
        return await asyncio.to_thread(
            self._list_epics_sync,
            project_id,
            limit,
            offset,
        )

    def _list_epics_sync(
        self,
        project_id: ProjectId | None,
        limit: int,
        offset: int,
    ) -> list[Epic]:
        """Synchronous list_epics for thread execution."""
        # Get epic IDs (filtered or all)
        # smembers() returns set[str] for synchronous Redis client
        epic_ids_set: set[str]
        if project_id:
            epic_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._epics_by_project_key(project_id)
            )
        else:
            epic_ids_set = self.client.smembers(self._all_epics_set_key())  # type: ignore[assignment]

        epic_ids = list(epic_ids_set)

        # Sort by ID (creation order approximation)
        epic_ids.sort()

        # Apply pagination
        paginated_ids = epic_ids[offset : offset + limit]

        # Retrieve full epics synchronously
        epics = []
        for epic_id_str in paginated_ids:
            epic = self._get_epic_sync(EpicId(epic_id_str))
            if epic:
                epics.append(epic)

        return epics

    async def delete_epic(self, epic_id: EpicId) -> None:
        """
        Delete epic from Valkey permanent storage.

        Deletes:
        - Hash with all fields
        - Epic ID from sets (all, project)

        Args:
            epic_id: ID of epic to delete.
        """
        # Get current project_id to remove from sets
        hash_key = self._epic_hash_key(epic_id)
        project_id_str = self.client.hget(hash_key, "project_id")

        # Delete hash
        self.client.delete(hash_key)

        # Remove from all epics set
        self.client.srem(self._all_epics_set_key(), epic_id.value)

        # Remove from project-specific set
        if project_id_str:
            self.client.srem(
                self._epics_by_project_key(ProjectId(project_id_str)),
                epic_id.value,
            )

        logger.info(f"Epic deleted from Valkey: {epic_id}")

    # ========== Task Methods ==========

    def _task_hash_key(self, task_id: TaskId) -> str:
        """Generate hash key for task details."""
        return ValkeyKeys.task_hash(task_id)

    def _all_tasks_set_key(self) -> str:
        """Key for set containing all task IDs."""
        return ValkeyKeys.all_tasks()

    def _tasks_by_story_set_key(self, story_id: StoryId) -> str:
        """Key for set containing task IDs by story."""
        return ValkeyKeys.tasks_by_story(story_id)

    def _tasks_by_plan_set_key(self, plan_id: PlanId) -> str:
        """Key for set containing task IDs by plan."""
        return ValkeyKeys.tasks_by_plan(plan_id)

    async def save_task(self, task: Task) -> None:
        """
        Persist task details to Valkey (permanent storage).

        Stores:
        - Hash with all task fields (permanent, no TTL)
        - Task ID in sets for indexing (all, story, plan if exists)

        Args:
            task: Task to persist.

        Raises:
            ValueError: If task.story_id is empty (domain invariant violation)
        """
        if not task.story_id:
            raise ValueError("Task story_id is required (domain invariant)")

        # Get old plan_id to update sets if needed
        hash_key = self._task_hash_key(task.task_id)
        old_plan_id_str = self.client.hget(hash_key, "plan_id")

        # Store task as hash (all fields) using mapper
        task_data = TaskValkeyMapper.to_dict(task)
        self.client.hset(hash_key, mapping=task_data)

        # Add to all tasks set
        self.client.sadd(self._all_tasks_set_key(), task.task_id.value)

        # Add to story-specific set (REQUIRED - domain invariant)
        self.client.sadd(
            self._tasks_by_story_set_key(task.story_id),
            task.task_id.value,
        )

        # Handle Plan set update (OPTIONAL)
        if task.plan_id:
            # Add to plan-specific set
            self.client.sadd(
                self._tasks_by_plan_set_key(task.plan_id),
                task.task_id.value,
            )

        # If plan_id changed, update plan sets
        if old_plan_id_str and old_plan_id_str != (task.plan_id.value if task.plan_id else ""):
            # Remove from old plan set
            old_plan_key = self._tasks_by_plan_set_key(PlanId(old_plan_id_str))
            self.client.srem(old_plan_key, task.task_id.value)

            # Add to new plan set if exists
            if task.plan_id:
                self.client.sadd(
                    self._tasks_by_plan_set_key(task.plan_id),
                    task.task_id.value,
                )

        logger.info(f"Task saved to Valkey: {task.task_id} (story: {task.story_id})")

    async def get_task(self, task_id: TaskId) -> Task | None:
        """
        Retrieve task from Valkey permanent storage.

        Args:
            task_id: ID of task to retrieve.

        Returns:
            Task if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_task_sync, task_id)

    def _get_task_sync(self, task_id: TaskId) -> Task | None:
        """Synchronous get_task for thread execution."""
        hash_key = self._task_hash_key(task_id)
        data = self.client.hgetall(hash_key)

        if not data:
            return None

        try:
            return TaskValkeyMapper.from_dict(data)
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to deserialize task {task_id}: {e}")
            return None

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
        return await asyncio.to_thread(
            self._list_tasks_sync,
            story_id,
            limit,
            offset,
        )

    def _list_tasks_sync(
        self,
        story_id: StoryId | None,
        limit: int,
        offset: int,
    ) -> list[Task]:
        """Synchronous list_tasks for thread execution."""
        # Get task IDs from sets
        # smembers() returns set[str] for synchronous Redis client
        task_ids_set: set[str]

        if story_id:
            task_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._tasks_by_story_set_key(story_id)
            )
        else:
            task_ids_set = self.client.smembers(self._all_tasks_set_key())  # type: ignore[assignment]

        task_ids = list(task_ids_set)

        # Sort by ID (creation order approximation)
        task_ids.sort()

        # Apply pagination
        paginated_ids = task_ids[offset : offset + limit]

        # Retrieve full tasks synchronously
        tasks = []
        for task_id_str in paginated_ids:
            task = self._get_task_sync(TaskId(task_id_str))
            if task:
                tasks.append(task)

        return tasks

    # ========== Backlog Review Ceremony PO Approval Methods ==========

    async def save_ceremony_story_po_approval(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        po_notes: str,
        approved_by: str,
        approved_at: str,
        po_concerns: str | None = None,
        priority_adjustment: str | None = None,
        po_priority_reason: str | None = None,
        plan_id: str | None = None,
    ) -> None:
        """
        Save PO approval details (po_notes, po_concerns, etc.) to Valkey.

        This stores semantic context of PO approval decisions in Valkey (permanent storage),
        separate from Neo4j graph structure.

        Args:
            ceremony_id: Ceremony identifier.
            story_id: Story identifier.
            po_notes: PO explains WHY they approve (REQUIRED).
            approved_by: User who approved.
            approved_at: ISO timestamp of approval.
            po_concerns: Optional PO concerns or risks to monitor.
            priority_adjustment: Optional priority override (HIGH, MEDIUM, LOW).
            po_priority_reason: Required if priority_adjustment provided.
            plan_id: Optional plan ID created after approval (for idempotency checks).
        """
        key = ValkeyKeys.ceremony_story_po_approval(ceremony_id, story_id)
        approval_data = {
            "po_notes": po_notes,
            "approved_by": approved_by,
            "approved_at": approved_at,
        }
        if po_concerns:
            approval_data["po_concerns"] = po_concerns
        if priority_adjustment:
            approval_data["priority_adjustment"] = priority_adjustment
        if po_priority_reason:
            approval_data["po_priority_reason"] = po_priority_reason
        if plan_id:
            approval_data["plan_id"] = plan_id

        await asyncio.to_thread(self.client.hset, key, mapping=approval_data)
        logger.info(
            f"PO approval saved to Valkey: ceremony={ceremony_id.value}, "
            f"story={story_id.value}"
        )

    async def get_ceremony_story_po_approval(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> dict[str, str] | None:
        """
        Retrieve PO approval details from Valkey.

        Args:
            ceremony_id: Ceremony identifier.
            story_id: Story identifier.

        Returns:
            Dict with po_notes, approved_by, approved_at, po_concerns (optional),
            priority_adjustment (optional), po_priority_reason (optional),
            or None if not found.
        """
        key = ValkeyKeys.ceremony_story_po_approval(ceremony_id, story_id)
        data = await asyncio.to_thread(self.client.hgetall, key)
        if not data:
            logger.debug(
                f"No PO approval found in Valkey: ceremony={ceremony_id.value}, "
                f"story={story_id.value}"
            )
            return None

        # Ensure all values are strings (decode if bytes)
        decoded_data: dict[str, str] = {}
        for k, v in data.items():
            key_str = k.decode("utf-8") if isinstance(k, bytes) else k
            value_str = v.decode("utf-8") if isinstance(v, bytes) else v
            decoded_data[key_str] = value_str

        logger.info(
            f"Retrieved PO approval from Valkey: ceremony={ceremony_id.value}, "
            f"story={story_id.value}, po_notes={'present' if decoded_data.get('po_notes') else 'missing'}"
        )
        return decoded_data

    async def get_story_po_approvals(
        self,
        story_id: StoryId,
    ) -> list[StoryPoApproval]:
        """
        Retrieve all PO approval details for a story from Valkey.

        Searches all ceremonies that have po_approval data for this story.
        Uses SCAN to find all keys matching the pattern:
        planning:ceremony:*:story:{story_id}:po_approval

        Args:
            story_id: Story identifier.

        Returns:
            List of StoryPoApproval value objects, each representing a PO approval
            decision for this story in a specific ceremony.

        Raises:
            ValueError: If data from Valkey is invalid (missing required fields)
        """
        from datetime import datetime

        from planning.domain.value_objects.actors.user_name import UserName

        # Pattern to match: planning:ceremony:*:story:{story_id}:po_approval
        pattern = f"{ValkeyKeys.NAMESPACE}:ceremony:*:story:{story_id.value}:po_approval"

        # Use SCAN to find all matching keys
        matching_keys: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await asyncio.to_thread(
                self.client.scan, cursor, match=pattern, count=100
            )
            matching_keys.extend(keys)
            if cursor == 0:
                break

        # Retrieve approval data for each key and convert to domain entity
        approvals: list[StoryPoApproval] = []
        for key in matching_keys:
            data = await asyncio.to_thread(self.client.hgetall, key)
            if not data:
                continue

            # Extract ceremony_id from key
            # Key format: planning:ceremony:{ceremony_id}:story:{story_id}:po_approval
            parts = key.split(":")
            if len(parts) < 3:
                logger.warning(f"Invalid key format: {key}, skipping")
                continue

            ceremony_id_str = parts[2]

            # Validate required fields
            if not data.get("po_notes"):
                logger.warning(
                    f"Missing po_notes in approval data for ceremony {ceremony_id_str}, skipping"
                )
                continue
            if not data.get("approved_by"):
                logger.warning(
                    f"Missing approved_by in approval data for ceremony {ceremony_id_str}, skipping"
                )
                continue
            if not data.get("approved_at"):
                logger.warning(
                    f"Missing approved_at in approval data for ceremony {ceremony_id_str}, skipping"
                )
                continue

            try:
                # Convert to domain entity using value objects
                po_notes_vo = PoNotes(data["po_notes"])
                po_concerns_vo = (
                    PoConcerns(data["po_concerns"]) if data.get("po_concerns") else None
                )
                priority_adjustment_vo = (
                    PriorityAdjustment.from_string(data["priority_adjustment"])
                    if data.get("priority_adjustment")
                    else None
                )

                approval = StoryPoApproval(
                    ceremony_id=BacklogReviewCeremonyId(ceremony_id_str),
                    story_id=story_id,
                    approved_by=UserName(data["approved_by"]),
                    approved_at=datetime.fromisoformat(data["approved_at"]),
                    po_notes=po_notes_vo,
                    po_concerns=po_concerns_vo,
                    priority_adjustment=priority_adjustment_vo,
                )
                approvals.append(approval)
            except (ValueError, KeyError) as e:
                logger.warning(
                    f"Error creating StoryPoApproval from Valkey data: {e}, skipping"
                )
                continue

        logger.debug(f"Found {len(approvals)} PO approvals for story {story_id.value}")
        return approvals

