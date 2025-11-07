"""Valkey (Redis) cache adapter for workflow state.

Provides fast caching layer on top of Neo4j persistence.
Following Hexagonal Architecture (Adapter).
"""

import json
from datetime import datetime

import valkey.asyncio as valkey
from core.shared.domain import Action, ActionEnum

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


class ValkeyWorkflowCacheAdapter(WorkflowStateRepositoryPort):
    """Valkey cache adapter for workflow state.

    Write-through cache pattern:
    - get_state: Cache hit → return, Cache miss → fetch from DB, cache, return
    - save_state: Write to DB → invalidate/update cache
    - get_pending_by_role: Always query DB (no caching for lists)

    Cache keys:
    - workflow:state:{task_id} → WorkflowState JSON
    - TTL: 1 hour (3600 seconds)

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure implementation)
    - Implements WorkflowStateRepositoryPort (application port)
    - Decorates another repository (Neo4j) with caching
    """

    def __init__(
        self,
        valkey_client: valkey.Valkey,
        primary_repository: WorkflowStateRepositoryPort,
        ttl_seconds: int = 3600,
    ) -> None:
        """Initialize cache adapter.

        Args:
            valkey_client: Valkey async client
            primary_repository: Primary repository (Neo4j)
            ttl_seconds: Cache TTL in seconds (default 1 hour)
        """
        self._valkey = valkey_client
        self._primary = primary_repository
        self._ttl = ttl_seconds

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
            return self._from_json(cached)

        # Cache miss: fetch from primary
        state = await self._primary.get_state(task_id)

        if state:
            # Populate cache
            await self._valkey.setex(
                cache_key,
                self._ttl,
                self._to_json(state),
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

        # Update cache
        cache_key = f"workflow:state:{state.task_id}"
        await self._valkey.setex(
            cache_key,
            self._ttl,
            self._to_json(state),
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

    def _to_json(self, state: WorkflowState) -> str:
        """Serialize WorkflowState to JSON.

        This is infrastructure responsibility (mapper logic).
        Domain entities do NOT know about JSON.

        Args:
            state: WorkflowState to serialize

        Returns:
            JSON string
        """
        data = {
            "task_id": str(state.task_id),
            "story_id": str(state.story_id),
            "current_state": state.current_state.value,
            "role_in_charge": str(state.role_in_charge) if state.role_in_charge else None,
            "required_action": state.required_action.value.value if state.required_action else None,
            "feedback": state.feedback,
            "updated_at": state.updated_at.isoformat(),
            "retry_count": state.retry_count,
            "history": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "action": t.action.value.value,  # Action.value.value
                    "actor_role": str(t.actor_role),
                    "timestamp": t.timestamp.isoformat(),
                    "feedback": t.feedback,
                }
                for t in state.history
            ],
        }

        return json.dumps(data)

    def _from_json(self, json_str: str | bytes) -> WorkflowState:
        """Deserialize WorkflowState from JSON.

        This is infrastructure responsibility (mapper logic).

        Args:
            json_str: JSON string

        Returns:
            WorkflowState domain entity
        """
        data = json.loads(json_str)

        # Parse transitions
        transitions = []
        for t_data in data["history"]:
            transitions.append(
                StateTransition(
                    from_state=t_data["from_state"],
                    to_state=t_data["to_state"],
                    action=Action(value=ActionEnum(t_data["action"])),
                    actor_role=Role(t_data["actor_role"]),
                    timestamp=datetime.fromisoformat(t_data["timestamp"]),
                    feedback=t_data.get("feedback"),
                )
            )

        # Parse role_in_charge
        role_in_charge = None
        if data.get("role_in_charge"):
            role_in_charge = Role(data["role_in_charge"])

        # Parse required_action
        required_action = None
        if data.get("required_action"):
            required_action = Action(value=ActionEnum(data["required_action"]))

        return WorkflowState(
            task_id=TaskId(data["task_id"]),
            story_id=StoryId(data["story_id"]),
            current_state=WorkflowStateEnum(data["current_state"]),
            role_in_charge=role_in_charge,
            required_action=required_action,
            history=tuple(transitions),
            feedback=data.get("feedback"),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            retry_count=data.get("retry_count", 0),
        )

