"""Service for reconciling dual write operations.

Following Hexagonal Architecture:
- Application layer service
- Orchestrates reconciliation of failed Neo4j writes
- Uses ports (DualWriteLedgerPort, StoragePort) not concrete adapters
"""

import logging
from typing import Any

from planning.application.ports.dual_write_ledger_port import DualWriteLedgerPort
from planning.application.ports.storage_port import StoragePort
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter

logger = logging.getLogger(__name__)


class DualWriteReconciliationService:
    """Service for reconciling dual write operations.

    Re-executes Neo4j operations that failed after successful Valkey writes.
    Ensures eventual consistency between Valkey (source of truth) and Neo4j (projection).

    Following Hexagonal Architecture:
    - Application layer service
    - Depends on ports, not concrete adapters
    - Orchestrates reconciliation logic
    """

    def __init__(
        self,
        dual_write_ledger: DualWriteLedgerPort,
        neo4j_adapter: Neo4jAdapter,
    ):
        """Initialize reconciliation service.

        Args:
            dual_write_ledger: Port for dual write ledger operations
            neo4j_adapter: Neo4j adapter for executing operations
        """
        self._ledger = dual_write_ledger
        self._neo4j = neo4j_adapter

    async def reconcile_operation(
        self,
        operation_id: str,
        operation_type: str,
        operation_data: dict[str, Any],
    ) -> None:
        """Reconcile a dual write operation.

        Re-executes the Neo4j operation based on operation_type and operation_data.
        Marks operation as COMPLETED if successful, or records failure if it fails again.

        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., "save_story", "save_task")
            operation_data: Operation-specific data needed for reconciliation

        Raises:
            ValueError: If operation_type is unsupported
            Exception: If Neo4j operation fails
        """
        logger.info(
            f"Starting reconciliation: operation_id={operation_id}, "
            f"operation_type={operation_type}"
        )

        try:
            # Re-execute Neo4j operation based on type
            if operation_type == "save_story":
                await self._reconcile_save_story(operation_data)
            elif operation_type == "save_task":
                await self._reconcile_save_task(operation_data)
            elif operation_type == "save_task_with_decision":
                await self._reconcile_save_task_with_decision(operation_data)
            elif operation_type == "save_project":
                await self._reconcile_save_project(operation_data)
            elif operation_type == "save_epic":
                await self._reconcile_save_epic(operation_data)
            elif operation_type == "update_story":
                await self._reconcile_update_story(operation_data)
            elif operation_type == "delete_story":
                await self._reconcile_delete_story(operation_data)
            elif operation_type == "delete_project":
                await self._reconcile_delete_project(operation_data)
            elif operation_type == "delete_epic":
                await self._reconcile_delete_epic(operation_data)
            else:
                raise ValueError(f"Unsupported operation_type: {operation_type}")

            # Mark as COMPLETED
            await self._ledger.mark_completed(operation_id)

            logger.info(f"Reconciliation completed: operation_id={operation_id}")

        except Exception as e:
            error_msg = str(e)
            await self._ledger.record_failure(operation_id, error_msg)

            logger.error(
                f"Reconciliation failed: operation_id={operation_id}, error: {error_msg}",
                exc_info=True,
            )
            raise

    async def _reconcile_save_story(self, operation_data: dict[str, Any]) -> None:
        """Reconcile save_story operation.

        Args:
            operation_data: Operation data with story_id, epic_id, title, created_by, initial_state

        Raises:
            Exception: If Neo4j operation fails
        """
        from planning.domain.value_objects.identifiers.epic_id import EpicId
        from planning.domain.value_objects.identifiers.story_id import StoryId
        from planning.domain.value_objects.content.title import Title
        from planning.domain.value_objects.statuses.story_state import (
            StoryState,
            StoryStateEnum,
        )

        story_id = StoryId(operation_data["story_id"])
        epic_id = EpicId(operation_data["epic_id"]) if operation_data.get("epic_id") else None
        title = Title(operation_data["title"])
        created_by = operation_data["created_by"]
        initial_state = StoryState(StoryStateEnum(operation_data["initial_state"]))

        await self._neo4j.create_story_node(
            story_id=story_id,
            epic_id=epic_id,
            title=title,
            created_by=created_by,
            initial_state=initial_state,
        )

    async def _reconcile_save_task(self, operation_data: dict[str, Any]) -> None:
        """Reconcile save_task operation.

        Args:
            operation_data: Operation data with task_id, story_id, status, task_type, plan_id

        Raises:
            Exception: If Neo4j operation fails
        """
        from planning.domain.value_objects.identifiers.story_id import StoryId
        from planning.domain.value_objects.identifiers.task_id import TaskId
        from planning.domain.value_objects.identifiers.plan_id import PlanId
        from planning.domain.value_objects.statuses.task_status import TaskStatus
        from planning.domain.value_objects.statuses.task_type import TaskType

        task_id = TaskId(operation_data["task_id"])
        story_id = StoryId(operation_data["story_id"])
        status = TaskStatus(operation_data["status"])
        task_type = TaskType(operation_data["task_type"])
        plan_id = PlanId(operation_data["plan_id"]) if operation_data.get("plan_id") else None

        await self._neo4j.create_task_node(
            task_id=task_id,
            story_id=story_id,
            status=status,
            task_type=task_type,
            plan_id=plan_id,
        )

    async def _reconcile_save_task_with_decision(
        self,
        operation_data: dict[str, Any],
    ) -> None:
        """Reconcile save_task_with_decision operation.

        Args:
            operation_data: Operation data with task info and decision_metadata

        Raises:
            Exception: If Neo4j operation fails
        """
        from planning.domain.value_objects.identifiers.story_id import StoryId
        from planning.domain.value_objects.identifiers.task_id import TaskId
        from planning.domain.value_objects.identifiers.plan_id import PlanId
        from planning.domain.value_objects.statuses.task_status import TaskStatus
        from planning.domain.value_objects.statuses.task_type import TaskType

        task_id = TaskId(operation_data["task_id"])
        story_id = StoryId(operation_data["story_id"])
        plan_id = PlanId(operation_data["plan_id"])
        status = TaskStatus(operation_data["status"])
        task_type = TaskType(operation_data["task_type"])
        priority = operation_data.get("priority")
        decision_metadata = operation_data["decision_metadata"]

        await self._neo4j.create_task_node_with_semantic_relationship(
            task_id=task_id,
            story_id=story_id,
            plan_id=plan_id,
            status=status,
            task_type=task_type,
            priority=priority,
            decision_metadata=decision_metadata,
        )

    async def _reconcile_save_project(self, operation_data: dict[str, Any]) -> None:
        """Reconcile save_project operation.

        Args:
            operation_data: Operation data with project info

        Raises:
            Exception: If Neo4j operation fails
        """
        await self._neo4j.create_project_node(
            project_id=operation_data["project_id"],
            name=operation_data["name"],
            status=operation_data["status"],
            created_at=operation_data["created_at"],
            updated_at=operation_data["updated_at"],
        )

    async def _reconcile_save_epic(self, operation_data: dict[str, Any]) -> None:
        """Reconcile save_epic operation.

        Args:
            operation_data: Operation data with epic info

        Raises:
            Exception: If Neo4j operation fails
        """
        await self._neo4j.create_epic_node(
            epic_id=operation_data["epic_id"],
            project_id=operation_data["project_id"],
            name=operation_data["name"],
            status=operation_data["status"],
            created_at=operation_data["created_at"],
            updated_at=operation_data["updated_at"],
        )

    async def _reconcile_update_story(self, operation_data: dict[str, Any]) -> None:
        """Reconcile update_story operation.

        Args:
            operation_data: Operation data with story_id and new_state

        Raises:
            Exception: If Neo4j operation fails
        """
        from planning.domain.value_objects.identifiers.story_id import StoryId
        from planning.domain.value_objects.statuses.story_state import (
            StoryState,
            StoryStateEnum,
        )

        story_id = StoryId(operation_data["story_id"])
        new_state = StoryState(StoryStateEnum(operation_data["new_state"]))

        await self._neo4j.update_story_state(story_id=story_id, new_state=new_state)

    async def _reconcile_delete_story(self, operation_data: dict[str, Any]) -> None:
        """Reconcile delete_story operation.

        Args:
            operation_data: Operation data with story_id

        Raises:
            Exception: If Neo4j operation fails
        """
        from planning.domain.value_objects.identifiers.story_id import StoryId

        story_id = StoryId(operation_data["story_id"])
        await self._neo4j.delete_story_node(story_id)

    async def _reconcile_delete_project(self, operation_data: dict[str, Any]) -> None:
        """Reconcile delete_project operation.

        Args:
            operation_data: Operation data with project_id

        Raises:
            Exception: If Neo4j operation fails
        """
        await self._neo4j.delete_project_node(operation_data["project_id"])

    async def _reconcile_delete_epic(self, operation_data: dict[str, Any]) -> None:
        """Reconcile delete_epic operation.

        Args:
            operation_data: Operation data with epic_id

        Raises:
            Exception: If Neo4j operation fails
        """
        await self._neo4j.delete_epic_node(operation_data["epic_id"])
