"""Use case for processing derivation results."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from task_derivation.application.ports.messaging_port import MessagingPort
from task_derivation.application.ports.planning_port import PlanningPort
from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.commands.task_creation_command import (
    TaskCreationCommand,
)
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_graph import (
    DependencyGraph,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProcessTaskDerivationResultUseCase:
    """Persist derived tasks and publish events."""

    planning_port: PlanningPort
    messaging_port: MessagingPort
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)

    async def execute(
        self,
        *,
        plan_id: PlanId,
        story_id: StoryId,
        role: ContextRole,
        task_nodes: tuple[TaskNode, ...],
    ) -> None:
        if not task_nodes:
            raise ValueError("task_nodes cannot be empty")

        try:
            graph = DependencyGraph.from_tasks(task_nodes)
            plan = graph.get_execution_plan()

            commands = tuple(
                TaskCreationCommand(
                    plan_id=plan_id,
                    story_id=story_id,
                    title=step.task.title,
                    description=step.task.description,
                    estimated_hours=step.task.estimated_hours,
                    priority=step.task.priority,
                    assigned_role=role,
                )
                for step in plan
            )

            await self.planning_port.create_tasks(commands)

            if graph.dependencies:
                await self.planning_port.save_task_dependencies(
                    plan_id=plan_id,
                    story_id=story_id,
                    dependencies=graph.dependencies,
                )

            await self._publish_success(plan_id, story_id, len(commands), role)
        except Exception as exc:
            await self._publish_failure(plan_id, story_id, str(exc))
            logger.exception(
                "Failed to process derivation result for plan %s", plan_id.value
            )
            raise

    async def _publish_success(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        task_count: int,
        role: ContextRole,
    ) -> None:
        event = TaskDerivationCompletedEvent(
            plan_id=plan_id,
            story_id=story_id,
            task_count=task_count,
            role=role.value,
            occurred_at=self.clock(),
        )
        await self.messaging_port.publish_task_derivation_completed(event)

    async def _publish_failure(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        reason: str,
    ) -> None:
        event = TaskDerivationFailedEvent(
            plan_id=plan_id,
            story_id=story_id,
            reason=reason,
            requires_manual_review=True,
            occurred_at=self.clock(),
        )
        await self.messaging_port.publish_task_derivation_failed(event)

