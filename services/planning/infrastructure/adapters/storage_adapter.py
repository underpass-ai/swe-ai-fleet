"""Composite storage adapter coordinating Neo4j (graph) + Valkey (details)."""

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

from planning.application.ports import DualWriteLedgerPort, MessagingPort, StoragePort
from planning.domain import Story, StoryId, StoryList, StoryState
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.epic import Epic
from planning.domain.entities.plan import Plan
from planning.domain.entities.project import Project
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.review.story_po_approval import StoryPoApproval
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig
from planning.infrastructure.adapters.valkey_adapter import ValkeyConfig, ValkeyStorageAdapter
from planning.infrastructure.mappers.backlog_review_ceremony_storage_mapper import (
    BacklogReviewCeremonyStorageMapper,
)
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
        dual_write_ledger: DualWriteLedgerPort | None = None,
        messaging: MessagingPort | None = None,
    ):
        """
        Initialize composite storage adapter.

        Args:
            neo4j_config: Neo4j configuration (optional, uses env vars).
            valkey_config: Valkey configuration (optional, uses env vars).
            dual_write_ledger: Dual write ledger port for tracking operations (optional).
            messaging: Messaging port for publishing reconcile events (optional).
        """
        self.neo4j = Neo4jAdapter(config=neo4j_config)
        self.valkey = ValkeyStorageAdapter(config=valkey_config)
        self.dual_write_ledger = dual_write_ledger
        self.messaging = messaging

        logger.info("Composite storage initialized (Neo4j graph + Valkey details)")
        if self.dual_write_ledger:
            logger.info("Dual write ledger enabled")

    def _generate_operation_id(
        self,
        operation_type: str,
        entity_id: str,
    ) -> str:
        """Generate unique operation ID for dual write ledger.

        Args:
            operation_type: Type of operation (e.g., "save_story", "save_task")
            entity_id: Entity identifier (e.g., story_id, task_id)

        Returns:
            Unique operation ID (SHA-256 hash)
        """
        content = f"{operation_type}:{entity_id}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _execute_dual_write(
        self,
        operation_type: str,
        operation_id: str,
        valkey_operation: Callable[[], Any],
        neo4j_operation: Callable[[], Any],
        operation_data: dict[str, Any],
    ) -> None:
        """Execute dual write pattern with ledger tracking.

        Pattern:
        1. Write to Valkey (source of truth)
        2. Record PENDING in ledger
        3. Try Neo4j write
        4. If success -> mark COMPLETED
        5. If failure -> record_failure and publish reconcile event

        Args:
            operation_type: Type of operation (e.g., "save_story")
            operation_id: Unique operation identifier
            valkey_operation: Async callable that writes to Valkey
            neo4j_operation: Async callable that writes to Neo4j
            operation_data: Operation-specific data for reconciliation

        Raises:
            Exception: If Valkey write fails (fail-fast)
        """
        # 1. Write to Valkey (source of truth) - fail fast if this fails
        await valkey_operation()

        # 2. Record PENDING in ledger (if ledger is available)
        if self.dual_write_ledger:
            await self.dual_write_ledger.record_pending(operation_id)

        # 3. Try Neo4j write
        try:
            await neo4j_operation()

            # 4. Success -> mark COMPLETED
            if self.dual_write_ledger:
                await self.dual_write_ledger.mark_completed(operation_id)

            logger.info(f"Dual write completed: {operation_type} {operation_id}")

        except Exception as neo4j_error:
            # 5. Failure -> record_failure and publish reconcile event
            error_msg = str(neo4j_error)

            if self.dual_write_ledger:
                await self.dual_write_ledger.record_failure(operation_id, error_msg)

            if self.messaging:
                await self.messaging.publish_dualwrite_reconcile_requested(
                    operation_id=operation_id,
                    operation_type=operation_type,
                    operation_data=operation_data,
                )

            logger.warning(
                f"Neo4j write failed, reconciliation requested: {operation_type} "
                f"{operation_id}, error: {error_msg}"
            )
            # Note: We don't raise the exception here - Valkey write succeeded,
            # so the operation is considered successful from the caller's perspective

    def close(self) -> None:
        """Close all connections."""
        self.neo4j.close()
        self.valkey.close()
        logger.info("Storage adapter closed")

    async def save_story(self, story: Story) -> None:
        """
        Persist story to Neo4j (graph) + Valkey (details) using dual write ledger.

        Operations:
        1. Save full details to Valkey (source of truth)
        2. Record PENDING in ledger
        3. Create graph node in Neo4j (structure only)
        4. Mark COMPLETED if Neo4j succeeds, or publish reconcile event if it fails

        Args:
            story: Story to persist.

        Raises:
            Exception: If Valkey persistence fails (fail-fast).
            Note: Neo4j failures are handled gracefully via reconciliation.
        """
        operation_id = self._generate_operation_id(
            operation_type="save_story",
            entity_id=story.story_id.value,
        )

        operation_data = {
            "story_id": story.story_id.value,
            "epic_id": story.epic_id.value if story.epic_id else None,
            "title": story.title.value,
            "created_by": story.created_by.value,
            "initial_state": story.state.to_string(),  # Tell, Don't Ask
        }

        async def valkey_operation() -> None:
            await self.valkey.save_story(story)

        async def neo4j_operation() -> None:
            await self.neo4j.create_story_node(
                story_id=story.story_id,
                epic_id=story.epic_id,  # Pass EpicId Value Object directly (domain invariant)
                title=story.title,  # Pass Title Value Object directly
                created_by=story.created_by.value,  # Extract string value from UserName Value Object
                initial_state=story.state,
            )

        await self._execute_dual_write(
            operation_type="save_story",
            operation_id=operation_id,
            valkey_operation=valkey_operation,
            neo4j_operation=neo4j_operation,
            operation_data=operation_data,
        )

        logger.info(f"Story saved (dual write): {story.story_id}")

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

    async def save_task_with_decision(
        self,
        task: Task,
        decision_metadata: dict[str, str],
    ) -> None:
        """
        Persist task with semantic decision metadata to Neo4j + Valkey.

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

        Operations:
        1. Save full details to Valkey (same as save_task)
        2. Create task node in Neo4j with SEMANTIC HAS_TASK relationship

        Args:
            task: Task to persist
            decision_metadata: Dict with decision context:
                - decided_by (str): Council or actor
                - decision_reason (str): Why task exists
                - council_feedback (str): Full context
                - source (str): Origin of task
                - decided_at (str): ISO timestamp

        Raises:
            ValueError: If task.story_id or task.plan_id is empty, or required metadata missing
            Exception: If persistence fails
        """
        if not task.story_id:
            raise ValueError("Task story_id is required (domain invariant)")

        if not task.plan_id:
            raise ValueError(
                "Task plan_id is required for tasks with decisions "
                "(must be linked to approved plan)"
            )

        # Validate required decision metadata
        required_fields = ["decided_by", "decision_reason", "council_feedback", "source", "decided_at"]
        for field in required_fields:
            if field not in decision_metadata or not decision_metadata[field]:
                raise ValueError(
                    f"Required decision_metadata field '{field}' is missing or empty"
                )

        # 1. Save details to Valkey (permanent storage)
        await self.valkey.save_task(task)

        # 2. Create task node in Neo4j WITH semantic HAS_TASK relationship
        await self.neo4j.create_task_node_with_semantic_relationship(
            task_id=task.task_id,
            story_id=task.story_id,
            plan_id=task.plan_id,
            status=task.status,
            task_type=task.type,
            priority=task.priority,
            decision_metadata=decision_metadata,
        )

        logger.info(
            f"Task saved with decision metadata (dual): {task.task_id} "
            f"(story: {task.story_id}, decided_by: {decision_metadata['decided_by']})"
        )

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

    async def save_plan(self, plan: Plan) -> None:
        """Persist plan to Valkey as source of truth."""
        await self.valkey.save_plan(plan)
        logger.info("Plan saved: %s", plan.plan_id.value)

    async def get_plan(self, plan_id: PlanId) -> Plan | None:
        """Retrieve plan from Valkey source of truth."""
        return await self.valkey.get_plan(plan_id)

    async def save_task_with_deliberations(
        self,
        task: Task,
        deliberation_indices: list[int],
        ceremony_id: BacklogReviewCeremonyId,
    ) -> None:
        """Persist a task with associated agent deliberations.

        Creates task node and stores relationship to agent deliberations in Neo4j.
        Stores deliberation indices in task metadata for observability.

        Args:
            task: Task to persist
            deliberation_indices: List of indices into ceremony's agent_deliberations
            ceremony_id: Ceremony identifier (for retrieving deliberations)

        Raises:
            StorageError: If persistence fails
        """
        # First, save the task normally
        await self.save_task(task)

        # Then, store the relationship to deliberations in Neo4j
        # We'll store this as a property on the task node for now
        # In the future, we can create explicit relationships to deliberation nodes
        try:
            query = """
            MATCH (t:Task {task_id: $task_id})
            SET t.deliberation_indices = $deliberation_indices,
                t.ceremony_id = $ceremony_id,
                t.source = 'BACKLOG_REVIEW_DELIBERATION'
            """
            await self.neo4j.execute_write(
                query,
                {
                    "task_id": task.task_id.value,
                    "deliberation_indices": json.dumps(deliberation_indices),
                    "ceremony_id": ceremony_id.value,
                },
            )
            logger.info(
                f"Stored task {task.task_id.value} with {len(deliberation_indices)} "
                f"associated deliberations from ceremony {ceremony_id.value}"
            )
        except Exception as e:
            logger.error(
                f"Failed to store deliberation relationship for task {task.task_id.value}: {e}",
                exc_info=True,
            )
            # Don't fail the entire operation - task is already saved
            raise

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

    async def delete_project(self, project_id: ProjectId) -> None:
        """
        Delete project from Valkey + Neo4j.

        Operations:
        1. Delete from Valkey
        2. Delete node from Neo4j graph

        Args:
            project_id: ID of project to delete.
        """
        # 1. Delete from Valkey
        await self.valkey.delete_project(project_id)

        # 2. Delete node from Neo4j graph
        await self.neo4j.delete_project_node(project_id.value)

        logger.info(f"Project deleted (dual): {project_id}")

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

    async def delete_epic(self, epic_id: EpicId) -> None:
        """
        Delete epic from Valkey + Neo4j.

        Operations:
        1. Delete from Valkey
        2. Delete node from Neo4j graph

        Args:
            epic_id: ID of epic to delete.
        """
        # 1. Delete from Valkey
        await self.valkey.delete_epic(epic_id)

        # 2. Delete node from Neo4j graph
        await self.neo4j.delete_epic_node(epic_id.value)

        logger.info(f"Epic deleted (dual): {epic_id}")

    # ========== Backlog Review Ceremony Methods ==========

    async def _get_project_id_from_ceremony(
        self, ceremony: "BacklogReviewCeremony"
    ) -> str | None:
        """Extract project_id from ceremony's first story.

        Args:
            ceremony: BacklogReviewCeremony entity

        Returns:
            Project ID string if found, None otherwise
        """
        if not ceremony.story_ids:
            return None

        first_story = await self.get_story(ceremony.story_ids[0])
        if not first_story:
            return None

        epic = await self.get_epic(first_story.epic_id)
        if not epic:
            return None

        return epic.project_id.value

    async def _save_po_approvals_to_valkey(
        self, ceremony: "BacklogReviewCeremony"
    ) -> None:
        """Save PO approval details to Valkey for approved review results.

        Args:
            ceremony: BacklogReviewCeremony entity

        Raises:
            ValueError: If approved review result is missing required fields
        """
        ceremony_id_vo = BacklogReviewCeremonyId(ceremony.ceremony_id.value)

        for review_result in ceremony.review_results:
            if not (
                review_result.approval_status.is_approved()
                and review_result.po_notes
            ):
                continue

            # Validate that approved_by and approved_at are present (domain invariant)
            if not review_result.approved_by:
                raise ValueError(
                    f"Approved review result for story {review_result.story_id.value} "
                    "must have approved_by (domain invariant)"
                )
            if not review_result.approved_at:
                raise ValueError(
                    f"Approved review result for story {review_result.story_id.value} "
                    "must have approved_at (domain invariant)"
                )

            # Save po_approval to Valkey (include plan_id for idempotency checks)
            await self.valkey.save_ceremony_story_po_approval(
                ceremony_id=ceremony_id_vo,
                story_id=review_result.story_id,
                po_notes=review_result.po_notes,
                approved_by=review_result.approved_by.value,
                approved_at=review_result.approved_at.isoformat(),
                po_concerns=review_result.po_concerns,
                priority_adjustment=review_result.priority_adjustment,
                plan_id=review_result.plan_id.value if review_result.plan_id else None,
            )

    async def save_backlog_review_ceremony(
        self,
        ceremony: "BacklogReviewCeremony",
    ) -> None:
        """
        Persist BacklogReviewCeremony using dual persistence pattern.

        Storage Strategy:
        - Neo4j: Graph structure, relationships, state, review results (without po_notes)
        - Valkey: PO approval details (po_notes, po_concerns, priority_adjustment, etc.)

        Neo4j:
        - Store ceremony node with all properties (review_results_json WITHOUT po_notes)
        - Create REVIEWS relationships to stories
        - Create BELONGS_TO relationship to project

        Valkey:
        - Store po_approval details for each approved review result
        - Key: planning:ceremony:{ceremony_id}:story:{story_id}:po_approval
        - Contains: po_notes, approved_by, approved_at, po_concerns, priority_adjustment, po_priority_reason

        Args:
            ceremony: BacklogReviewCeremony entity to persist

        Raises:
            StorageError: If persistence fails
        """
        logger.info(f"Saving ceremony: {ceremony.ceremony_id.value}")

        # Get project_id from first story (all stories should belong to same project)
        project_id = await self._get_project_id_from_ceremony(ceremony)

        # Save to Neo4j (graph structure + relationships, review_results_json WITHOUT po_notes)
        neo4j_dict = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(ceremony)
        await self.neo4j.save_backlog_review_ceremony_node(
            ceremony_id=ceremony.ceremony_id.value,
            properties=neo4j_dict,
            story_ids=[sid.value for sid in ceremony.story_ids],
            project_id=project_id,
        )

        # Save PO approval details to Valkey (for approved review results)
        await self._save_po_approvals_to_valkey(ceremony)

        logger.info(f"Ceremony saved: {ceremony.ceremony_id.value} (Neo4j + Valkey)")

    async def get_backlog_review_ceremony(
        self,
        ceremony_id: "BacklogReviewCeremonyId",
    ) -> "BacklogReviewCeremony | None":
        """
        Retrieve BacklogReviewCeremony by ID using dual persistence pattern.

        Retrieval Strategy:
        - Neo4j: Graph structure, relationships, state, review results (without po_notes)
        - Valkey: PO approval details (po_notes, po_concerns, priority_adjustment, etc.)

        Args:
            ceremony_id: ID of ceremony to retrieve

        Returns:
            BacklogReviewCeremony if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        # Import here to avoid circular dependency
        from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
            BacklogReviewCeremonyId,
        )
        from planning.infrastructure.mappers.backlog_review_ceremony_storage_mapper import (
            BacklogReviewCeremonyStorageMapper,
        )

        # Query Neo4j for ceremony structure
        neo4j_result = await self.neo4j.get_backlog_review_ceremony_node(
            ceremony_id.value
        )

        if not neo4j_result:
            return None

        # Retrieve PO approval details from Valkey for all stories in ceremony
        ceremony_id_vo = BacklogReviewCeremonyId(ceremony_id.value)
        po_approvals: dict[str, dict[str, str]] = {}

        for story_id_str in neo4j_result["story_ids"]:
            from planning.domain.value_objects.identifiers.story_id import StoryId

            story_id_vo = StoryId(story_id_str)
            po_approval = await self.valkey.get_ceremony_story_po_approval(
                ceremony_id=ceremony_id_vo, story_id=story_id_vo
            )
            if po_approval:
                po_approvals[story_id_str] = po_approval
                logger.info(
                    f"Retrieved po_approval from Valkey: ceremony={ceremony_id.value}, "
                    f"story={story_id_str}, po_notes={'present' if po_approval.get('po_notes') else 'missing'}"
                )
            else:
                logger.info(
                    f"No po_approval found in Valkey: ceremony={ceremony_id.value}, "
                    f"story={story_id_str}"
                )

        # Reconstruct ceremony from Neo4j data + Valkey po_approvals
        ceremony = BacklogReviewCeremonyStorageMapper.from_neo4j_dict(
            data=neo4j_result["properties"],
            story_ids=neo4j_result["story_ids"],
            review_results_json=neo4j_result.get("review_results_json", "[]"),
            po_approvals=po_approvals if po_approvals else None,
        )

        return ceremony

    async def list_backlog_review_ceremonies(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list["BacklogReviewCeremony"]:
        """
        List backlog review ceremonies using dual persistence pattern.

        Retrieves ceremonies from Neo4j and combines with PO approval details from Valkey.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of BacklogReviewCeremony entities

        Raises:
            StorageError: If query fails
        """
        # Import here to avoid circular dependency
        from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
            BacklogReviewCeremonyId,
        )
        from planning.domain.value_objects.identifiers.story_id import StoryId
        from planning.infrastructure.mappers.backlog_review_ceremony_storage_mapper import (
            BacklogReviewCeremonyStorageMapper,
        )

        neo4j_results = await self.neo4j.list_backlog_review_ceremony_nodes(
            limit=limit,
            offset=offset,
        )

        ceremonies = []
        for result in neo4j_results:
            # Retrieve PO approval details from Valkey for all stories in ceremony
            ceremony_id_vo = BacklogReviewCeremonyId(result["properties"]["ceremony_id"])
            po_approvals: dict[str, dict[str, str]] = {}

            for story_id_str in result["story_ids"]:
                story_id_vo = StoryId(story_id_str)
                po_approval = await self.valkey.get_ceremony_story_po_approval(
                    ceremony_id=ceremony_id_vo, story_id=story_id_vo
                )
                if po_approval:
                    po_approvals[story_id_str] = po_approval

            # Reconstruct ceremony from Neo4j data + Valkey po_approvals
            ceremony = BacklogReviewCeremonyStorageMapper.from_neo4j_dict(
                data=result["properties"],
                story_ids=result["story_ids"],
                review_results_json=result.get("review_results_json", "[]"),
                po_approvals=po_approvals if po_approvals else None,
            )
            ceremonies.append(ceremony)

        return ceremonies

    async def get_story_po_approvals(
        self,
        story_id: StoryId,
    ) -> list[StoryPoApproval]:
        """
        Retrieve all PO approval details (po_notes) for a story from Valkey.

        This method searches all ceremonies that have po_approval data for this story.
        Useful when displaying tasks for a story - you can also show the PO's approval notes.

        Args:
            story_id: Story identifier.

        Returns:
            List of StoryPoApproval value objects, each representing a PO approval
            decision for this story in a specific ceremony.

        Example usage:
            tasks = await storage.list_tasks(story_id=story_id)
            po_approvals = await storage.get_story_po_approvals(story_id=story_id)
            # Display tasks with PO approval context grouped by story
        """
        return await self.valkey.get_story_po_approvals(story_id)

    async def get_ceremony_story_po_approval(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> dict[str, str] | None:
        """
        Retrieve PO approval details for a specific ceremony and story from Valkey (source-of-truth).

        This method provides direct access to Valkey for idempotency checks.
        Valkey is the source-of-truth for PO approvals, so this check happens before
        any Neo4j synchronization.

        Args:
            ceremony_id: Ceremony identifier.
            story_id: Story identifier.

        Returns:
            Dict with po_notes, approved_by, approved_at, plan_id (optional),
            po_concerns (optional), priority_adjustment (optional),
            po_priority_reason (optional), or None if not found.
        """
        return await self.valkey.get_ceremony_story_po_approval(ceremony_id, story_id)
