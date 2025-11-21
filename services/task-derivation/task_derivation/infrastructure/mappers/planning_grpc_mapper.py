"""Mapper between Planning Service gRPC protos and domain/value objects."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from core.shared.domain.value_objects.task_attributes.priority import Priority

from task_derivation.domain.value_objects.content.acceptance_criteria import (
    AcceptanceCriteria,
)
from task_derivation.domain.value_objects.content.plan_description import PlanDescription
from task_derivation.domain.value_objects.content.technical_notes import TechnicalNotes
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.commands.task_creation_command import (
    TaskCreationCommand,
)
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)
from task_derivation.domain.value_objects.task_derivation.summary.task_summary import (
    TaskSummary,
)

ProtoMessage = TypeVar("ProtoMessage")


@dataclass(frozen=True)
class PlanningGrpcMapper:
    """Pure mapper for Planning gRPC messages ↔ domain objects."""

    @staticmethod
    def plan_context_from_proto(message: Any) -> PlanContext:
        """Convert proto PlanContext into domain PlanContext VO."""
        if not getattr(message, "plan_id", None):
            raise ValueError("plan_id is required")
        if not getattr(message, "story_id", None):
            raise ValueError("story_id is required")
        if not getattr(message, "title", None):
            raise ValueError("title is required")
        if not getattr(message, "description", None):
            raise ValueError("description is required")

        acceptance_values = list(getattr(message, "acceptance_criteria", []) or [])
        if not acceptance_values:
            raise ValueError("acceptance_criteria cannot be empty")

        roles_raw = list(getattr(message, "roles", []) or [])
        if not roles_raw:
            raise ValueError("roles cannot be empty")

        return PlanContext(
            plan_id=PlanId(message.plan_id),
            story_id=StoryId(message.story_id),
            title=Title(message.title),
            description=PlanDescription(message.description),
            acceptance_criteria=AcceptanceCriteria.from_iterable(acceptance_values),
            technical_notes=TechnicalNotes(getattr(message, "technical_notes", "")),
            roles=tuple(ContextRole(role) for role in roles_raw),
        )

    @staticmethod
    def task_summary_from_proto(message: Any) -> TaskSummary:
        """Convert proto TaskSummary into domain TaskSummary VO."""
        if not getattr(message, "task_id", None):
            raise ValueError("task_id is required")
        if not getattr(message, "title", None):
            raise ValueError("title is required")

        return TaskSummary(
            task_id=TaskId(message.task_id),
            title=Title(message.title),
            priority=Priority(getattr(message, "priority")),
            assigned_role=ContextRole(getattr(message, "assigned_role", "")),
        )

    @staticmethod
    def task_summary_list_from_proto(messages: Iterable[Any]) -> tuple[TaskSummary, ...]:
        """Convert iterable of proto TaskSummary messages to domain tuple."""
        return tuple(
            PlanningGrpcMapper.task_summary_from_proto(message) for message in messages
        )

    @staticmethod
    def task_creation_command_to_proto(
        command: TaskCreationCommand,
        proto_cls: type[ProtoMessage],
    ) -> ProtoMessage:
        """Convert domain TaskCreationCommand into proto message."""
        return proto_cls(
            plan_id=command.plan_id.value,
            story_id=command.story_id.value,
            title=command.title.value,
            description=command.description.value,
            estimated_hours=command.estimated_hours.to_hours(),
            priority=command.priority.to_int(),
            assigned_role=str(command.assigned_role),
        )

    @staticmethod
    def dependency_edge_to_proto(
        edge: DependencyEdge,
        proto_cls: type[ProtoMessage],
    ) -> ProtoMessage:
        """Convert domain DependencyEdge into proto message."""
        return proto_cls(
            from_task_id=edge.from_task_id.value,
            to_task_id=edge.to_task_id.value,
            reason=edge.reason.value,
        )

    @staticmethod
    def dependency_edges_to_proto(
        edges: Sequence[DependencyEdge],
        proto_cls: type[ProtoMessage],
    ) -> list[ProtoMessage]:
        """Convert sequence of domain DependencyEdges into list of proto messages."""
        return [
            PlanningGrpcMapper.dependency_edge_to_proto(edge, proto_cls)
            for edge in edges
        ]

