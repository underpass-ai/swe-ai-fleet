"""Valkey (Redis) cache adapter for workflow state.

Provides fast caching layer on top of Neo4j persistence.
Following Hexagonal Architecture (Adapter).
"""

import redis.asyncio as valkey  # Valkey is Redis-compatible

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.infrastructure.mappers.workflow_state_mapper import (
    WorkflowStateMapper,
)


class ValkeyWorkflowCacheAdapter(WorkflowStateRepositoryPort):
    """Valkey cache adapter for workflow state.

    Write-through cache pattern:
    - get_state: Cache hit → return, Cache miss → fetch from DB, cache, return
    - save_state: Write to DB → invalidate/update cache
    - get_pending_by_role: Always query DB (no caching for lists)

    Cache keys:
    - workflow:state:{task_id} → WorkflowState JSON (no TTL, persistent)

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure implementation)
    - Implements WorkflowStateRepositoryPort (application port)
    - Decorates another repository (Neo4j) with caching
    """

    def __init__(
        self,
        valkey_client: valkey.Valkey,
        primary_repository: WorkflowStateRepositoryPort,
    ) -> None:
        """Initialize cache adapter.

        Args:
            valkey_client: Valkey async client
            primary_repository: Primary repository (Neo4j)

        Note: No TTL - workflow state is persistent until explicitly deleted.
        """
        self._valkey = valkey_client
        self._primary = primary_repository

    async def get_state(self, task_id: TaskId) -> WorkflowState | None:
        """Get workflow state (cache-first).

        Args:
            task_id: Task identifier

        Returns:
            WorkflowState if found, None otherwise
        """
        cache_key = f"workflow:state:{task_id}"

        # Try cache first
        cached = await self._valkey.get(cache_key)
        if cached:
            return WorkflowStateMapper.from_json(cached)

        # Cache miss: fetch from primary
        state = await self._primary.get_state(task_id)

        if state:
            # Populate cache (no TTL - persistent)
            await self._valkey.set(
                cache_key,
                WorkflowStateMapper.to_json(state),
            )

        return state

    async def save_state(self, state: WorkflowState) -> None:
        """Save workflow state (write-through).

        Writes to primary repository and updates cache.

        Args:
            state: Workflow state to persist
        """
        # Write to primary
        await self._primary.save_state(state)

        # Update cache (no TTL - persistent)
        cache_key = f"workflow:state:{state.task_id}"
        await self._valkey.set(
            cache_key,
            WorkflowStateMapper.to_json(state),
        )

    async def get_pending_by_role(self, role: str, limit: int = 100) -> list[WorkflowState]:
        """Get pending tasks (no caching for lists).

        Lists are not cached (too dynamic, hard to invalidate).
        Always queries primary repository.

        Args:
            role: Role identifier
            limit: Maximum number of results

        Returns:
            List of WorkflowState instances
        """
        return await self._primary.get_pending_by_role(role, limit)

    async def get_all_by_story(self, story_id: StoryId) -> list[WorkflowState]:
        """Get all workflow states for a story (no caching).

        Args:
            story_id: Story identifier

        Returns:
            List of WorkflowState instances
        """
        return await self._primary.get_all_by_story(story_id)

    async def delete_state(self, task_id: TaskId) -> None:
        """Delete workflow state (invalidate cache).

        Args:
            task_id: Task identifier
        """
        # Delete from primary
        await self._primary.delete_state(task_id)

        # Invalidate cache
        cache_key = f"workflow:state:{task_id}"
        await self._valkey.delete(cache_key)

