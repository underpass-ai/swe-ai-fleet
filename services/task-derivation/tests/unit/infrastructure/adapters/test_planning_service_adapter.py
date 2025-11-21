"""Tests for PlanningServiceAdapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from core.shared.domain.value_objects.content.task_description import (
    TaskDescription,
)
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority

from task_derivation.domain.value_objects.content.dependency_reason import (
    DependencyReason,
)
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
from task_derivation.infrastructure.adapters.planning_service_adapter import (
    PlanningServiceAdapter,
)
from task_derivation.infrastructure.mappers.planning_grpc_mapper import (
    PlanningGrpcMapper,
)


class FakePlanContextProto:
    def __init__(self) -> None:
        self.plan_id = "plan-1"
        self.story_id = "story-1"
        self.title = "Title"
        self.description = "Description"
        self.acceptance_criteria = ["AC1"]
        self.technical_notes = "Notes"
        self.roles = ["DEV"]


class FakeTaskSummaryProto:
    def __init__(self, task_id: str, title: str, priority: int, role: str) -> None:
        self.task_id = task_id
        self.title = title
        self.priority = priority
        self.assigned_role = role


class FakeTaskCreationCommandProto:
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


class FakeTaskDerivationPb2:
    TaskCreationCommand = FakeTaskCreationCommandProto
    DependencyEdge = FakeDependencyEdgeProto

    class GetPlanContextRequest:
        def __init__(self, plan_id: str) -> None:
            self.plan_id = plan_id

    class CreateTasksRequest:
        def __init__(self, commands: list[Any]) -> None:
            self.commands = commands

    class ListStoryTasksRequest:
        def __init__(self, story_id: str) -> None:
            self.story_id = story_id

    class SaveTaskDependenciesRequest:
        def __init__(self, plan_id: str, story_id: str, edges: list[Any]) -> None:
            self.plan_id = plan_id
            self.story_id = story_id
            self.edges = edges


class FakePlanningStub:
    def __init__(self) -> None:
        self.plan_requests: list[Any] = []
        self.create_requests: list[Any] = []
        self.list_requests: list[Any] = []
        self.dependencies_requests: list[Any] = []

    async def GetPlanContext(self, request: Any, timeout: float | None = None) -> Any:
        self.plan_requests.append(request)
        return SimpleNamespace(plan_context=FakePlanContextProto())

    async def CreateTasks(self, request: Any, timeout: float | None = None) -> Any:
        self.create_requests.append(request)
        return SimpleNamespace(task_ids=["task-1", "task-2"])

    async def ListStoryTasks(self, request: Any, timeout: float | None = None) -> Any:
        self.list_requests.append(request)
        return SimpleNamespace(
            tasks=[
                FakeTaskSummaryProto("task-1", "t1", 1, "DEV"),
                FakeTaskSummaryProto("task-2", "t2", 2, "QA"),
            ]
        )

    async def SaveTaskDependencies(self, request: Any, timeout: float | None = None) -> Any:
        self.dependencies_requests.append(request)
        return SimpleNamespace()


@pytest.fixture(autouse=True)
def patch_pb2(monkeypatch: pytest.MonkeyPatch) -> None:
    import task_derivation.infrastructure.adapters.planning_service_adapter as module

    monkeypatch.setattr(module, "task_derivation_pb2", FakeTaskDerivationPb2, raising=False)


@pytest.fixture
def adapter_with_stub(monkeypatch: pytest.MonkeyPatch) -> tuple[PlanningServiceAdapter, FakePlanningStub]:
    stub = FakePlanningStub()
    adapter = PlanningServiceAdapter(
        address="localhost:5000",
        timeout_seconds=1.0,
        mapper=PlanningGrpcMapper(),
        stub=stub,
    )
    return adapter, stub


@pytest.mark.asyncio
async def test_get_plan_returns_context(adapter_with_stub: tuple[PlanningServiceAdapter, FakePlanningStub]) -> None:
    adapter, stub = adapter_with_stub

    plan = await adapter.get_plan(PlanId("plan-123"))

    assert isinstance(plan, PlanContext)
    assert plan.plan_id.value == "plan-1"  # from stub response
    assert stub.plan_requests[0].plan_id == "plan-123"


@pytest.mark.asyncio
async def test_create_tasks_returns_task_ids(adapter_with_stub: tuple[PlanningServiceAdapter, FakePlanningStub]) -> None:
    adapter, stub = adapter_with_stub
    commands = (
        TaskCreationCommand(
            plan_id=PlanId("plan-1"),
            story_id=StoryId("story-1"),
            title=Title("Task"),
            description=TaskDescription("desc"),
            estimated_hours=Duration(4),
            priority=Priority(1),
            assigned_role=ContextRole("DEV"),
        ),
    )

    result = await adapter.create_tasks(commands)

    assert result == (TaskId("task-1"), TaskId("task-2"))
    assert len(stub.create_requests[0].commands) == 1


@pytest.mark.asyncio
async def test_list_story_tasks_maps_results(adapter_with_stub: tuple[PlanningServiceAdapter, FakePlanningStub]) -> None:
    adapter, stub = adapter_with_stub

    summaries = await adapter.list_story_tasks(StoryId("story-42"))
    assert len(summaries) == 2
    assert isinstance(summaries[0], TaskSummary)
    assert stub.list_requests[0].story_id == "story-42"


@pytest.mark.asyncio
async def test_save_task_dependencies_sends_edges(adapter_with_stub: tuple[PlanningServiceAdapter, FakePlanningStub]) -> None:
    adapter, stub = adapter_with_stub
    edges = (
        DependencyEdge(
            from_task_id=TaskId("task-1"),
            to_task_id=TaskId("task-2"),
            reason=DependencyReason("blocked"),
        ),
    )

    await adapter.save_task_dependencies(PlanId("plan"), StoryId("story"), edges)
    request = stub.dependencies_requests[0]
    assert request.plan_id == "plan"
    assert request.edges[0].reason == "blocked"

