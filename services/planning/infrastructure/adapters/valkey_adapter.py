"""Valkey (Redis-compatible) adapter for Planning Service - Permanent Storage."""

import asyncio
import logging

import redis
from planning.application.ports import StoragePort
from planning.domain import Story, StoryId, StoryList, StoryState, StoryStateEnum
from planning.domain.entities.epic import Epic
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys
from planning.infrastructure.mappers.epic_valkey_mapper import EpicValkeyMapper
from planning.infrastructure.mappers.project_valkey_mapper import ProjectValkeyMapper
from planning.infrastructure.mappers.story_valkey_mapper import StoryValkeyMapper

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
        # smembers() returns set[str] for synchronous Redis client
        story_ids_set: set[str]
        if state_filter:
            story_ids_set = self.client.smembers(  # type: ignore[assignment]
                self._stories_by_state_set_key(state_filter)
            )
        else:
            story_ids_set = self.client.smembers(self._all_stories_set_key())  # type: ignore[assignment]

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

