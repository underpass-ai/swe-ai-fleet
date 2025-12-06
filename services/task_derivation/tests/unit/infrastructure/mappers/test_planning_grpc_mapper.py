"""Tests for PlanningGrpcMapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from core.shared.domain.value_objects.content.task_description import (
    TaskDescription,
)
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from task_derivation.domain.value_objects.content.dependency_reason import DependencyReason
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
from task_derivation.infrastructure.mappers.planning_grpc_mapper import (
    PlanningGrpcMapper,
)


class FakeTaskCreationCommandProto:
    """Test double mimicking generated proto constructor."""

    def __init__(
        self,
        plan_id: str,
        story_id: str,
        title: str,
        description: str,
        estimated_hours: int,
        priority: int,
        assigned_role: str,
    ) -> None:
        self.plan_id = plan_id
        self.story_id = story_id
        self.title = title
        self.description = description
        self.estimated_hours = estimated_hours
        self.priority = priority
        self.assigned_role = assigned_role


class FakeDependencyEdgeProto:
    def __init__(self, from_task_id: str, to_task_id: str, reason: str) -> None:
        self.from_task_id = from_task_id
        self.to_task_id = to_task_id
        self.reason = reason


def test_plan_context_from_proto_success() -> None:
    message = SimpleNamespace(
        plan_id="plan-123",
        story_id="story-456",
        title="Implement feature",
        description="Detailed plan description",
        acceptance_criteria=["AC1", "AC2"],
        technical_notes="Use FastAPI",
        roles=["DEVELOPER", "QA"],
    )

    context = PlanningGrpcMapper.plan_context_from_proto(message)

    assert isinstance(context, PlanContext)
    assert context.plan_id.value == "plan-123"
    assert context.story_id.value == "story-456"
    assert context.title.value == "Implement feature"
    assert [criterion.value for criterion in context.acceptance_criteria] == [
        "AC1",
        "AC2",
    ]
    assert str(context.technical_notes) == "Use FastAPI"
    assert tuple(str(role) for role in context.roles) == ("DEVELOPER", "QA")


def test_plan_context_from_proto_rejects_missing_roles() -> None:
    message = SimpleNamespace(
        plan_id="plan-123",
        story_id="story-456",
        title="title",
        description="desc",
        acceptance_criteria=["AC1"],
        technical_notes="notes",
        roles=[],
    )

    with pytest.raises(ValueError):
        PlanningGrpcMapper.plan_context_from_proto(message)


def test_task_summary_from_proto() -> None:
    message = SimpleNamespace(
        task_id="task-1",
        title="Do something",
        priority=5,
        assigned_role="DEV",
    )

    summary = PlanningGrpcMapper.task_summary_from_proto(message)
    assert isinstance(summary, TaskSummary)
    assert summary.task_id.value == "task-1"
    assert summary.priority.to_int() == 5
    assert str(summary.assigned_role) == "DEV"


def test_task_creation_command_to_proto() -> None:
    command = TaskCreationCommand(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        title=Title("Implement"),
        description=TaskDescription("Do it"),
        estimated_hours=Duration(8),
        priority=Priority(2),
        assigned_role=ContextRole("DEV"),
    )

    proto = PlanningGrpcMapper.task_creation_command_to_proto(
        command,
        FakeTaskCreationCommandProto,
    )

    assert proto.plan_id == "plan-1"
    assert proto.estimated_hours == 8
    assert proto.assigned_role == "DEV"


def test_dependency_edge_to_proto() -> None:
    edge = DependencyEdge(
        from_task_id=TaskId("task-1"),
        to_task_id=TaskId("task-2"),
        reason=DependencyReason("Depends on output"),
    )

    proto = PlanningGrpcMapper.dependency_edge_to_proto(
        edge,
        FakeDependencyEdgeProto,
    )

    assert proto.from_task_id == "task-1"
    assert proto.to_task_id == "task-2"
    assert proto.reason == "Depends on output"


def test_task_summary_list_from_proto() -> None:
    """Test converting iterable of proto TaskSummary messages to domain tuple."""
    messages = [
        SimpleNamespace(
            task_id="task-1",
            title="Task 1",
            priority=1,
            assigned_role="DEV",
        ),
        SimpleNamespace(
            task_id="task-2",
            title="Task 2",
            priority=2,
            assigned_role="QA",
        ),
        SimpleNamespace(
            task_id="task-3",
            title="Task 3",
            priority=3,
            assigned_role="PO",
        ),
    ]

    summaries = PlanningGrpcMapper.task_summary_list_from_proto(messages)

    assert isinstance(summaries, tuple)
    assert len(summaries) == 3
    assert summaries[0].task_id.value == "task-1"
    assert summaries[0].title.value == "Task 1"
    assert summaries[0].priority.to_int() == 1
    assert str(summaries[0].assigned_role) == "DEV"
    assert summaries[1].task_id.value == "task-2"
    assert summaries[2].task_id.value == "task-3"


def test_task_summary_list_from_proto_empty() -> None:
    """Test converting empty iterable returns empty tuple."""
    messages: list[SimpleNamespace] = []

    summaries = PlanningGrpcMapper.task_summary_list_from_proto(messages)

    assert isinstance(summaries, tuple)
    assert len(summaries) == 0


def test_dependency_edges_to_proto() -> None:
    """Test converting sequence of DependencyEdge to list of proto messages."""
    edges = [
        DependencyEdge(
            from_task_id=TaskId("task-1"),
            to_task_id=TaskId("task-2"),
            reason=DependencyReason("Task 2 needs output from Task 1"),
        ),
        DependencyEdge(
            from_task_id=TaskId("task-2"),
            to_task_id=TaskId("task-3"),
            reason=DependencyReason("Task 3 depends on Task 2"),
        ),
    ]

    protos = PlanningGrpcMapper.dependency_edges_to_proto(
        edges,
        FakeDependencyEdgeProto,
    )

    assert isinstance(protos, list)
    assert len(protos) == 2
    assert protos[0].from_task_id == "task-1"
    assert protos[0].to_task_id == "task-2"
    assert protos[0].reason == "Task 2 needs output from Task 1"
    assert protos[1].from_task_id == "task-2"
    assert protos[1].to_task_id == "task-3"
    assert protos[1].reason == "Task 3 depends on Task 2"


def test_dependency_edges_to_proto_empty() -> None:
    """Test converting empty sequence returns empty list."""
    edges: list[DependencyEdge] = []

    protos = PlanningGrpcMapper.dependency_edges_to_proto(
        edges,
        FakeDependencyEdgeProto,
    )

    assert isinstance(protos, list)
    assert len(protos) == 0


