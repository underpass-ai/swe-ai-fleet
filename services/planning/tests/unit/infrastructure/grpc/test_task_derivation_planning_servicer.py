"""Unit tests for TaskDerivationPlanningServiceServicer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc.aio import ServicerContext
from planning.domain.entities.plan import Plan
from planning.domain.entities.task import Task
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import task_derivation_pb2
from planning.infrastructure.grpc.task_derivation_planning_servicer import (
    TaskDerivationPlanningServiceServicer,
)


@pytest.fixture
def mock_context() -> MagicMock:
    """Create mock gRPC context."""
    context = MagicMock(spec=ServicerContext)
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@pytest.fixture
def servicer() -> TaskDerivationPlanningServiceServicer:
    """Create servicer with mocked dependencies."""
    storage = AsyncMock()
    create_task_uc = AsyncMock()
    list_tasks_uc = AsyncMock()
    return TaskDerivationPlanningServiceServicer(
        storage=storage,
        create_task_uc=create_task_uc,
        list_tasks_uc=list_tasks_uc,
    )


@pytest.fixture
def sample_plan() -> Plan:
    """Create sample plan entity."""
    return Plan(
        plan_id=PlanId("PL-001"),
        story_ids=(StoryId("story-123"),),
        title=Title("Plan title"),
        description=Brief("Plan description"),
        acceptance_criteria=("AC-1",),
        technical_notes="Use retries",
        roles=("DEV", "QA"),
    )


@pytest.mark.asyncio
async def test_get_plan_context_success(
    servicer: TaskDerivationPlanningServiceServicer,
    sample_plan: Plan,
    mock_context: MagicMock,
) -> None:
    """GetPlanContext returns mapped plan context when plan exists."""
    servicer._storage.get_plan.return_value = sample_plan  # type: ignore[attr-defined]

    response = await servicer.GetPlanContext(
        task_derivation_pb2.GetPlanContextRequest(plan_id="PL-001"),
        mock_context,
    )

    assert response.plan_context.plan_id == "PL-001"
    assert response.plan_context.story_id == "story-123"
    assert response.plan_context.title == "Plan title"
    assert response.plan_context.acceptance_criteria == ["AC-1"]
    assert response.plan_context.roles == ["DEV", "QA"]
    servicer._storage.get_plan.assert_awaited_once_with(PlanId("PL-001"))  # type: ignore[attr-defined]
    mock_context.set_code.assert_not_called()


@pytest.mark.asyncio
async def test_get_plan_context_not_found(
    servicer: TaskDerivationPlanningServiceServicer,
    mock_context: MagicMock,
) -> None:
    """GetPlanContext returns NOT_FOUND when plan does not exist."""
    servicer._storage.get_plan.return_value = None  # type: ignore[attr-defined]

    response = await servicer.GetPlanContext(
        task_derivation_pb2.GetPlanContextRequest(plan_id="PL-MISSING"),
        mock_context,
    )

    assert not response.HasField("plan_context")
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)
    mock_context.set_details.assert_called_once()


@pytest.mark.asyncio
async def test_create_tasks_success(
    servicer: TaskDerivationPlanningServiceServicer,
    mock_context: MagicMock,
) -> None:
    """CreateTasks creates each command and returns generated task IDs."""

    async def _fake_execute(create_request):
        now = datetime.now(UTC)
        return Task(
            task_id=create_request.task_id,
            story_id=create_request.story_id,
            title=create_request.title.value,
            created_at=now,
            updated_at=now,
            plan_id=create_request.plan_id,
            description=create_request.description.value,
            assigned_to=str(create_request.assigned_to),
            estimated_hours=create_request.estimated_hours.to_hours(),
            type=TaskType.DEVELOPMENT,
            status=TaskStatus.TODO,
            priority=create_request.priority.to_int(),
        )

    servicer._create_task_uc.execute.side_effect = _fake_execute  # type: ignore[attr-defined]
    request = task_derivation_pb2.CreateTasksRequest(
        commands=[
            task_derivation_pb2.TaskCreationCommand(
                plan_id="PL-001",
                story_id="story-123",
                title="Create endpoint",
                description="Expose endpoint",
                estimated_hours=4,
                priority=1,
                assigned_role="DEV",
            ),
            task_derivation_pb2.TaskCreationCommand(
                plan_id="PL-001",
                story_id="story-123",
                title="Add tests",
                description="",
                estimated_hours=2,
                priority=2,
                assigned_role="QA",
            ),
        ]
    )

    response = await servicer.CreateTasks(request, mock_context)

    assert len(response.task_ids) == 2
    assert response.task_ids[0].startswith("T-")
    assert response.task_ids[1].startswith("T-")
    assert servicer._create_task_uc.execute.await_count == 2  # type: ignore[attr-defined]
    mock_context.set_code.assert_not_called()


@pytest.mark.asyncio
async def test_list_story_tasks_success(
    servicer: TaskDerivationPlanningServiceServicer,
    mock_context: MagicMock,
) -> None:
    """ListStoryTasks maps Task entities to TaskSummary proto messages."""
    now = datetime.now(UTC)
    servicer._list_tasks_uc.execute.return_value = [  # type: ignore[attr-defined]
        Task(
            task_id=TaskId("T-001"),
            story_id=StoryId("story-123"),
            title="Existing task",
            created_at=now,
            updated_at=now,
            plan_id=PlanId("PL-001"),
            description="desc",
            assigned_to="DEV",
            estimated_hours=3,
            type=TaskType.DEVELOPMENT,
            status=TaskStatus.TODO,
            priority=1,
        )
    ]

    response = await servicer.ListStoryTasks(
        task_derivation_pb2.ListStoryTasksRequest(story_id="story-123"),
        mock_context,
    )

    assert len(response.tasks) == 1
    assert response.tasks[0].task_id == "T-001"
    assert response.tasks[0].assigned_role == "DEV"
    servicer._list_tasks_uc.execute.assert_awaited_once_with(  # type: ignore[attr-defined]
        story_id=StoryId("story-123"),
        plan_id=None,
        limit=1000,
        offset=0,
    )
    mock_context.set_code.assert_not_called()


@pytest.mark.asyncio
async def test_save_task_dependencies_success(
    servicer: TaskDerivationPlanningServiceServicer,
    mock_context: MagicMock,
) -> None:
    """SaveTaskDependencies persists mapped dependency edges."""
    request = task_derivation_pb2.SaveTaskDependenciesRequest(
        plan_id="PL-001",
        story_id="story-123",
        edges=[
            task_derivation_pb2.DependencyEdge(
                from_task_id="T-001",
                to_task_id="T-002",
                reason="blocks",
            )
        ],
    )

    response = await servicer.SaveTaskDependencies(request, mock_context)

    assert response.success is True
    servicer._storage.save_task_dependencies.assert_awaited_once()  # type: ignore[attr-defined]
    saved_edges = servicer._storage.save_task_dependencies.await_args.args[0]  # type: ignore[attr-defined]
    assert len(saved_edges) == 1
    assert saved_edges[0].from_task_id.value == "T-001"
    assert saved_edges[0].to_task_id.value == "T-002"
    assert saved_edges[0].reason.value == "blocks"
    mock_context.set_code.assert_not_called()

