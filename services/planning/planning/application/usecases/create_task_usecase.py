"""CreateTaskUseCase - Create new task within a story."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain.entities.task import Task
from planning.domain.value_objects.plan_id import PlanId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.task_id import TaskId
from planning.domain.value_objects.task_status import TaskStatus
from planning.domain.value_objects.task_type import TaskType

logger = logging.getLogger(__name__)


@dataclass
class CreateTaskUseCase:
    """Create a new task within a plan.

    This use case:
    1. Validates that parent plan (and story) exists
    2. Creates Task domain entity
    3. Persists to dual storage (Neo4j + Valkey)
    4. Creates PlanVersion→Task relationship in Neo4j
    5. Publishes planning.task.created event

    Following Hexagonal Architecture:
    - Depends on ports (StoragePort, MessagingPort)
    - Returns domain entity (Task)
    - No infrastructure dependencies
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        title: str,
        description: str = "",
        type: TaskType = TaskType.DEVELOPMENT,
        assigned_to: str = "",
        estimated_hours: int = 0,
        priority: int = 1,
    ) -> Task:
        """Execute task creation.

        Args:
            plan_id: Parent plan ID (REQUIRED - domain invariant)
            story_id: Story ID (for denormalization)
            title: Task title (REQUIRED)
            description: Optional task description
            type: Task type (DEVELOPMENT, TESTING, etc.)
            assigned_to: Agent or role assigned
            estimated_hours: Estimated effort in hours
            priority: Task priority (1 = highest)

        Returns:
            Created Task entity

        Raises:
            ValueError: If plan_id is empty or parent plan not found
        """
        # Step 1: Validate parent story exists (domain invariant enforcement)
        parent_story = await self.storage.get_story(story_id)
        if not parent_story:
            raise ValueError(
                f"Cannot create Task: Story {story_id} not found. "
                "Domain Invariant: Task MUST belong to an existing Story (via Plan)."
            )

        # Step 2: Generate task ID using UUID for guaranteed uniqueness
        task_id = TaskId(f"T-{uuid4()}")

        # Step 3: Create Task domain entity (validation in __post_init__)
        now = datetime.now(UTC)
        task = Task(
            task_id=task_id,
            plan_id=plan_id,  # REQUIRED parent plan reference
            story_id=story_id,  # Denormalized for fast lookups
            title=title,
            description=description,
            type=type,
            status=TaskStatus.TODO,  # Initial status
            assigned_to=assigned_to,
            estimated_hours=estimated_hours,
            priority=priority,
            created_at=now,
            updated_at=now,
        )

        # Step 4: Persist to dual storage (Neo4j + Valkey)
        # Neo4j will also create PlanVersion→Task relationship
        await self.storage.save_task(task)

        logger.info(f"Task created: {task_id} - {title} (plan: {plan_id}, story: {story_id})")

        # Step 5: Publish event (other services react)
        # Use case creates domain event, mapper handles serialization
        from planning.domain.events.task_created_event import TaskCreatedEvent
        from planning.infrastructure.mappers.task_event_mapper import TaskEventMapper

        # Create domain event
        event = TaskEventMapper.task_to_created_event(task)

        # Convert to payload (infrastructure mapper)
        payload = TaskEventMapper.created_event_to_payload(event)

        # Publish via port
        await self.messaging.publish_event(
            topic="planning.task.created",
            payload=payload,
        )

        return task

