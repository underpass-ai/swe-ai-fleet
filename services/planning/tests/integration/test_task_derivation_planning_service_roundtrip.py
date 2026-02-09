"""Integration test for TaskDerivationPlanningService gRPC roundtrip."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import grpc
import pytest
from planning.domain.entities.plan import Plan
from planning.domain.entities.task import Task
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.requests.create_task_request import CreateTaskRequest
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import task_derivation_pb2, task_derivation_pb2_grpc
from planning.infrastructure.grpc.task_derivation_planning_servicer import (
    TaskDerivationPlanningServiceServicer,
)


@dataclass
class _InMemoryStorage:
    plan: Plan
    dependencies_saved: tuple = ()

    async def get_plan(self, plan_id: PlanId) -> Plan | None:
        if plan_id.value == self.plan.plan_id.value:
            return self.plan
        return None

    async def save_task_dependencies(self, dependencies: tuple) -> None:
        self.dependencies_saved = dependencies


@dataclass
class _InMemoryCreateTaskUseCase:
    tasks: list[Task]

    async def execute(self, request: CreateTaskRequest) -> Task:
        task = Task(
            task_id=request.task_id,
            story_id=request.story_id,
            title=request.title.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            plan_id=request.plan_id,
            description=request.description.value,
            assigned_to=str(request.assigned_to),
            estimated_hours=request.estimated_hours.to_hours(),
            type=TaskType.DEVELOPMENT,
            status=TaskStatus.TODO,
            priority=request.priority.to_int(),
        )
        self.tasks.append(task)
        return task


@dataclass
class _InMemoryListTasksUseCase:
    tasks: list[Task]

    async def execute(self, story_id, plan_id, limit, offset):  # noqa: ANN001 - test double
        del plan_id  # not used for this contract
        filtered = [task for task in self.tasks if task.story_id.value == story_id.value]
        return filtered[offset : offset + limit]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_task_derivation_planning_service_roundtrip() -> None:
    """All 4 RPCs execute on an implemented endpoint without UNIMPLEMENTED."""
    plan = Plan(
        plan_id=PlanId("PL-RT-001"),
        story_ids=(StoryId("story-rt-001"),),
        title=Title("Roundtrip plan"),
        description=Brief("Plan used for gRPC integration roundtrip"),
        acceptance_criteria=("AC-1",),
        technical_notes="Keep service contract stable",
        roles=("DEV",),
    )
    storage = _InMemoryStorage(plan=plan)
    tasks: list[Task] = []
    create_uc = _InMemoryCreateTaskUseCase(tasks=tasks)
    list_uc = _InMemoryListTasksUseCase(tasks=tasks)

    server = grpc.aio.server()
    servicer = TaskDerivationPlanningServiceServicer(
        storage=storage,
        create_task_uc=create_uc,  # type: ignore[arg-type]
        list_tasks_uc=list_uc,  # type: ignore[arg-type]
    )
    task_derivation_pb2_grpc.add_TaskDerivationPlanningServiceServicer_to_server(
        servicer,
        server,
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub(channel)

    try:
        context_response = await stub.GetPlanContext(
            task_derivation_pb2.GetPlanContextRequest(plan_id="PL-RT-001")
        )
        assert context_response.plan_context.story_id == "story-rt-001"

        create_response = await stub.CreateTasks(
            task_derivation_pb2.CreateTasksRequest(
                commands=[
                    task_derivation_pb2.TaskCreationCommand(
                        plan_id="PL-RT-001",
                        story_id="story-rt-001",
                        title="Implement endpoint",
                        description="",
                        estimated_hours=3,
                        priority=1,
                        assigned_role="DEV",
                    ),
                    task_derivation_pb2.TaskCreationCommand(
                        plan_id="PL-RT-001",
                        story_id="story-rt-001",
                        title="Add tests",
                        description="Integration + unit coverage",
                        estimated_hours=2,
                        priority=2,
                        assigned_role="QA",
                    ),
                ]
            )
        )
        assert len(create_response.task_ids) == 2

        list_response = await stub.ListStoryTasks(
            task_derivation_pb2.ListStoryTasksRequest(story_id="story-rt-001")
        )
        assert len(list_response.tasks) == 2
        assert list_response.tasks[0].task_id

        save_response = await stub.SaveTaskDependencies(
            task_derivation_pb2.SaveTaskDependenciesRequest(
                plan_id="PL-RT-001",
                story_id="story-rt-001",
                edges=[
                    task_derivation_pb2.DependencyEdge(
                        from_task_id=create_response.task_ids[0],
                        to_task_id=create_response.task_ids[1],
                        reason="Execution order",
                    )
                ],
            )
        )
        assert save_response.success is True
        assert len(storage.dependencies_saved) == 1
    finally:
        await channel.close()
        await server.stop(grace=0)
