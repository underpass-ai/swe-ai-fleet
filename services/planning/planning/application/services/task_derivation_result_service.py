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

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.value_objects.identifiers.plan_id import PlanId
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
    - Validate task derivation result
    - Build and validate dependency graph
    - Persist tasks in execution order (via CreateTaskUseCase)
    - Publish events (success/failure)
    - Handle circular dependencies (manual review)
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
            storage: Storage port for queries
            messaging: Messaging port for event publishing
        """
        self._create_task = create_task_usecase
        self._storage = storage
        self._messaging = messaging

    async def process(
        self,
        plan_id: PlanId,
        task_nodes: tuple[TaskNode, ...],
    ) -> None:
        """Process task derivation result.

        Args:
            plan_id: Plan identifier
            task_nodes: Parsed task nodes from LLM

        Raises:
            ValueError: If plan not found or validation fails
        """
        # 1. Validate input
        if not task_nodes:
            raise ValueError(f"No tasks provided for plan {plan_id}")

        logger.info(f"Processing {len(task_nodes)} derived tasks for plan {plan_id}")

        # 2. Build dependency graph (Tell, Don't Ask: graph validates itself)
        graph = DependencyGraph.from_tasks(task_nodes)

        # 3. Check for circular dependencies
        if graph.has_circular_dependency():
            logger.warning(f"Circular dependencies detected in plan {plan_id}")

            # Notify manual review needed
            await self._notify_manual_review(plan_id, "Circular dependencies detected")

            # Fail fast - don't persist invalid graph
            raise ValueError(f"Circular dependencies in plan {plan_id}")

        # 4. Get plan to extract story_id
        plan = await self._storage.get_plan(plan_id)

        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        story_id = plan.story_id

        # 5. Persist tasks in execution order (Tell, Don't Ask: graph orders itself)
        ordered_tasks = graph.get_ordered_tasks()

        logger.info(f"Creating {len(ordered_tasks)} tasks in dependency order")

        for index, task_node in enumerate(ordered_tasks):
            # Build request VO (NO primitives)
            request = CreateTaskRequest(
                plan_id=plan_id,
                story_id=story_id,
                task_id=task_node.task_id,
                title=task_node.title,
                description=task_node.description,
                task_type=TaskType.DEVELOPMENT,  # Default type
                assigned_to=task_node.role,
                estimated_hours=0,  # TODO: Extract from LLM
                priority=index + 1,  # Order determines priority
            )

            # Delegate to CreateTaskUseCase
            await self._create_task.execute(request)

            logger.debug(f"Created task {task_node.task_id} (priority {index + 1})")

        # 6. Publish success event
        await self._publish_tasks_derived_event(plan_id, len(task_nodes))

        logger.info(f"✅ Task derivation completed for plan {plan_id}")

        # TODO: Persist dependency relationships to Neo4j
        # await self._persist_dependencies(plan_id, graph.dependencies)

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

