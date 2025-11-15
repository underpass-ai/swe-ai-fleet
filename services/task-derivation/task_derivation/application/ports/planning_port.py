"""Port definitions for interactions with Planning Service."""

from __future__ import annotations

from typing import Protocol

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.domain.value_objects.task_derivation.commands.task_creation_command import (
    TaskCreationCommand,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)
from task_derivation.domain.value_objects.task_derivation.summary.task_summary import (
    TaskSummary,
)


class PlanningPort(Protocol):
    """Port for Planning Service gRPC integration."""

    async def get_plan(self, plan_id: PlanId) -> PlanContext:
        """Fetch immutable snapshot of plan data needed for derivation."""
        ...

    async def create_tasks(
        self,
        commands: tuple[TaskCreationCommand, ...],
    ) -> tuple[TaskId, ...]:
        """Persist derived tasks following dependency order."""
        ...

    async def list_story_tasks(self, story_id: StoryId) -> tuple[TaskSummary, ...]:
        """List existing tasks for a story to avoid duplicates."""
        ...

    async def save_task_dependencies(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        """Persist dependency edges in Planning graph storage."""
        ...

