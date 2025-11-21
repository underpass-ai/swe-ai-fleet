"""Application service for processing task derivation results from Ray Executor.

Application Layer (DDD):
- Orchestrates task derivation result processing
- Coordinates use cases and domain logic
- Validates dependency graph
- Persists tasks via delegation
- Publishes events
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.value_objects.actors.role_mapper import RoleMapper
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.domain.value_objects.requests.create_task_request import CreateTaskRequest
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.domain.value_objects.task_derivation.dependency_graph import DependencyGraph
from planning.domain.value_objects.task_derivation.task_node import TaskNode

logger = logging.getLogger(__name__)


class TaskDerivationResultService:
    """Application service for processing task derivation results.

    Application Service (DDD):
    - NOT a use case (not a direct user action)
    - Coordinates multiple operations
    - Orchestrates domain logic
    - Bridges infrastructure → domain

    Following Hexagonal Architecture:
    - Application layer (orchestration)
    - Coordinates domain logic
    - Delegates to use cases
    - Delegates to ports (storage, messaging)
    - Publishes domain events

    Responsibilities:
    - Parse LLM output (TaskNode VOs) - content only (title, description, estimated_hours, keywords, priority)
    - Generate IDs: Planning Service generates task_id, plan_id, story_id (REQUIRED - NOT from LLM)
    - Assign tasks: Planning Service decides assignment based on RBAC (LLM role is just a hint)
    - Build dependency graph: Dependencies inferred from keyword matching in graph context (NOT from TASK_ID)
    - Persist tasks in dependency order (via CreateTaskUseCase)
    - Persist dependency relationships to Neo4j graph
    - Publish events (success/failure)
    - Handle circular dependencies (manual review)

    ID Generation (Planning Service - REQUIRED):
    - task_id: Planning Service generates (e.g., "T-{uuid}") - REQUIRED
    - plan_id: Planning Service provides from context (plan approved event) - REQUIRED
    - story_id: Planning Service provides from context (derived from plan) - REQUIRED
    - LLM TASK_ID is only a reference/placeholder, NOT used as real TaskId

    Assignment (Planning Service + RBAC):
    - assigned_to: Planning Service decides based on RBAC permissions
    - LLM role (ROLE field) is just a hint/suggestion
    - Planning Service validates permissions before assignment

    Dependency Calculation:
    - Dependencies are NOT calculated from TASK_ID
    - Dependencies are inferred from keyword matching in graph context
    - Keyword matching: If task B mentions task A's keywords, B depends on A
    - Graph relationships stored in Neo4j for intelligent context analysis
    """

    def __init__(
        self,
        create_task_usecase: CreateTaskUseCase,
        storage: StoragePort,
        messaging: MessagingPort,
    ):
        """Initialize service with dependencies.

        Args:
            create_task_usecase: Use case for creating individual tasks
            storage: Storage port for persisting task dependencies (NOT for Plan queries)
            messaging: Messaging port for event publishing

        Note:
            Task depends on Story, not Plan. This service only uses information from context (Story).
            Storage is used only for persisting task dependencies, not for Plan lookups.
        """
        self._create_task = create_task_usecase
        self._storage = storage
        self._messaging = messaging

    async def process(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        role: str,
        task_nodes: tuple[TaskNode, ...],
    ) -> None:
        """Process task derivation result.

        Args:
            plan_id: Plan identifier (Sprint/Iteration - can contain multiple Stories)
            story_id: Story identifier (specific Story for which tasks are being derived)
            role: Role from context (comes from agent.response.completed event)
            task_nodes: Parsed task nodes from LLM

        Raises:
            ValueError: If validation fails

        Note:
            Task depends on Story, not Plan. This service only uses information from context (Story).
            Role comes from agent.response.completed event (context), not from Plan storage.
        """
        # 1. Validate input
        if not task_nodes:
            raise ValueError(f"No tasks provided for story {story_id}")

        if not role or not role.strip():
            raise ValueError(f"Role cannot be empty for story {story_id}")

        logger.info(
            f"Processing {len(task_nodes)} derived tasks for Story {story_id} "
            f"(Plan: {plan_id}, Role: {role})"
        )

        # 2. Build dependency graph (Tell, Don't Ask: graph validates itself)
        graph = DependencyGraph.from_tasks(task_nodes)

        # 3. Check for circular dependencies
        if graph.has_circular_dependency():
            logger.warning(f"Circular dependencies detected for Story {story_id}")

            # Notify manual review needed
            await self._notify_manual_review(plan_id, "Circular dependencies detected")

            # Fail fast - don't persist invalid graph
            raise ValueError(f"Circular dependencies for Story {story_id}")

        # 4. Map role from context (comes from agent.response.completed event)
        # Task depends on Story, so role comes from Story context, not Plan storage
        assigned_role = RoleMapper.from_string(role)
        logger.debug(f"Assigned role from context: {role} → {assigned_role}")

        # 5. Persist tasks in execution order (Tell, Don't Ask: graph orders itself)
        ordered_tasks = graph.get_ordered_tasks()

        logger.info(f"Creating {len(ordered_tasks)} tasks in dependency order")

        for index, task_node in enumerate(ordered_tasks):
            # Planning Service generates TaskId (NOT from LLM)
            # LLM TASK_ID is only a reference/placeholder, Planning Service creates real ID
            task_id = TaskId(f"T-{uuid4()}")  # Planning Service generates real TaskId

            # Build request VO (NO primitives)
            # Role comes from agent.response.completed event (context)
            # Task depends on Story, so role comes from Story context
            # TODO: Validate with RBAC before assignment

            request = CreateTaskRequest(
                plan_id=plan_id,  # Planning Service provides from context (REQUIRED)
                story_id=story_id,  # Planning Service provides from context (REQUIRED)
                task_id=task_id,  # Planning Service generates (REQUIRED - NOT from LLM)
                title=task_node.title,  # From LLM
                description=task_node.description,  # From LLM
                task_type=TaskType.DEVELOPMENT,  # System default
                assigned_to=assigned_role,  # From planning.plan.approved event (plan.roles)
                estimated_hours=task_node.estimated_hours,  # From LLM
                priority=task_node.priority,  # From LLM (vLLM or superior LLM decides priority)
            )

            # Delegate to CreateTaskUseCase
            await self._create_task.execute(request)

            logger.debug(f"Created task {task_id} (LLM ref: {task_node.task_id}, priority {index + 1})")

        # 6. Publish success event
        await self._publish_tasks_derived_event(plan_id, len(task_nodes))

        logger.info(f"✅ Task derivation completed for plan {plan_id}")

        # 7. Persist dependency relationships to Neo4j
        if graph.dependencies:
            await self._storage.save_task_dependencies(graph.dependencies)
            logger.info(f"Persisted {len(graph.dependencies)} dependency relationships")

    async def _publish_tasks_derived_event(
        self,
        plan_id: PlanId,
        count: int,
    ) -> None:
        """Publish planning.tasks.derived event.

        Args:
            plan_id: Plan identifier
            count: Number of tasks derived
        """
        try:
            payload = {
                "event_type": "tasks.derived",
                "plan_id": plan_id.value,
                "task_count": count,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            await self._messaging.publish_event(
                topic=str(NATSSubject.TASKS_DERIVED),
                payload=payload,
            )

            logger.info(f"Published tasks.derived event for plan {plan_id}")

        except Exception as e:
            # Log but don't fail - event publishing is not critical
            logger.warning(f"Failed to publish tasks.derived event: {e}")

    async def _notify_manual_review(
        self,
        plan_id: PlanId,
        reason: str,
    ) -> None:
        """Notify that manual review is required.

        Args:
            plan_id: Plan identifier
            reason: Why manual review is needed
        """
        try:
            payload = {
                "event_type": "task.derivation.failed",
                "plan_id": plan_id.value,
                "reason": reason,
                "requires_manual_review": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            await self._messaging.publish_event(
                topic="planning.task.derivation.failed",
                payload=payload,
            )

            logger.warning(f"Manual review required for plan {plan_id}: {reason}")

        except Exception as e:
            logger.error(f"Failed to publish manual review notification: {e}")

