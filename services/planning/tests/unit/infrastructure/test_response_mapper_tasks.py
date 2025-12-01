"""Unit tests for ResponseMapper task-related methods."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper


@pytest.fixture
def sample_task_with_plan():
    """Create a sample task with plan_id."""
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("T-001"),
        story_id=StoryId("STORY-001"),
        plan_id=PlanId("PLAN-001"),
        title="Test Task",
        description="Test description",
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_task_without_plan():
    """Create a sample task without plan_id."""
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("T-002"),
        story_id=StoryId("STORY-002"),
        plan_id=None,  # No plan_id
        title="Ad-hoc Task",
        description="Task without plan",
        type=TaskType.BUG_FIX,
        status=TaskStatus.IN_PROGRESS,
        created_at=now,
        updated_at=now,
    )


class TestCreateTaskResponse:
    """Tests for create_task_response method."""

    def test_create_task_response_with_task(self, sample_task_with_plan):
        """Test create_task_response with task."""
        response = ResponseMapper.create_task_response(
            success=True,
            message="Task created",
            task=sample_task_with_plan,
        )

        assert response.success is True
        assert response.message == "Task created"
        assert response.task.task_id == "T-001"
        assert response.task.story_id == "STORY-001"
        assert response.task.plan_id == "PLAN-001"
        assert response.task.title == "Test Task"
        assert response.task.description == "Test description"
        assert response.task.type == "development"
        assert response.task.status == "todo"

    def test_create_task_response_with_task_no_plan(self, sample_task_without_plan):
        """Test create_task_response with task without plan_id."""
        response = ResponseMapper.create_task_response(
            success=True,
            message="Task created",
            task=sample_task_without_plan,
        )

        assert response.success is True
        assert response.message == "Task created"
        assert response.task.task_id == "T-002"
        assert response.task.story_id == "STORY-002"
        assert response.task.plan_id == ""  # Empty string when None
        assert response.task.title == "Ad-hoc Task"

    def test_create_task_response_without_task(self):
        """Test create_task_response without task (error case)."""
        response = ResponseMapper.create_task_response(
            success=False,
            message="Task creation failed",
            task=None,
        )

        assert response.success is False
        assert response.message == "Task creation failed"
        # When task is None, protobuf should not have task field set
        # (depends on protobuf implementation)


class TestTaskResponse:
    """Tests for task_response method."""

    def test_task_response_with_task(self, sample_task_with_plan):
        """Test task_response with task."""
        response = ResponseMapper.task_response(
            success=True,
            message="Task found",
            task=sample_task_with_plan,
        )

        assert response.success is True
        assert response.message == "Task found"
        assert response.task.task_id == "T-001"
        assert response.task.story_id == "STORY-001"
        assert response.task.plan_id == "PLAN-001"

    def test_task_response_with_task_no_plan(self, sample_task_without_plan):
        """Test task_response with task without plan_id."""
        response = ResponseMapper.task_response(
            success=True,
            message="Task found",
            task=sample_task_without_plan,
        )

        assert response.success is True
        assert response.task.task_id == "T-002"
        assert response.task.story_id == "STORY-002"
        assert response.task.plan_id == ""  # Empty string when None

    def test_task_response_without_task(self):
        """Test task_response without task (not found case)."""
        response = ResponseMapper.task_response(
            success=False,
            message="Task not found",
            task=None,
        )

        assert response.success is False
        assert response.message == "Task not found"

    def test_task_response_defaults(self):
        """Test task_response with default parameters."""
        response = ResponseMapper.task_response()

        assert response.success is False
        assert response.message == ""


class TestListTasksResponse:
    """Tests for list_tasks_response method."""

    def test_list_tasks_response_with_tasks(self, sample_task_with_plan, sample_task_without_plan):
        """Test list_tasks_response with multiple tasks."""
        tasks = [sample_task_with_plan, sample_task_without_plan]
        response = ResponseMapper.list_tasks_response(
            success=True,
            message="Found 2 tasks",
            tasks=tasks,
        )

        assert response.success is True
        assert response.message == "Found 2 tasks"
        assert response.total_count == 2
        assert len(response.tasks) == 2
        assert response.tasks[0].task_id == "T-001"
        assert response.tasks[1].task_id == "T-002"

    def test_list_tasks_response_empty(self):
        """Test list_tasks_response with empty list."""
        response = ResponseMapper.list_tasks_response(
            success=True,
            message="No tasks found",
            tasks=[],
        )

        assert response.success is True
        assert response.message == "No tasks found"
        assert response.total_count == 0
        assert len(response.tasks) == 0

    def test_list_tasks_response_none_tasks(self):
        """Test list_tasks_response with None tasks (defaults to empty list)."""
        response = ResponseMapper.list_tasks_response(
            success=True,
            message="No tasks",
            tasks=None,
        )

        assert response.success is True
        assert response.message == "No tasks"
        assert response.total_count == 0
        assert len(response.tasks) == 0


class TestTaskToProto:
    """Tests for _task_to_proto method."""

    def test_task_to_proto_with_plan(self, sample_task_with_plan):
        """Test _task_to_proto with task that has plan_id."""
        proto_task = ResponseMapper._task_to_proto(sample_task_with_plan)

        assert proto_task.task_id == "T-001"
        assert proto_task.story_id == "STORY-001"
        assert proto_task.plan_id == "PLAN-001"
        assert proto_task.title == "Test Task"
        assert proto_task.description == "Test description"
        assert proto_task.type == "development"
        assert proto_task.status == "todo"
        assert proto_task.assigned_to == ""
        assert proto_task.estimated_hours == 0
        assert proto_task.priority == 1
        assert proto_task.created_at is not None
        assert proto_task.updated_at is not None

    def test_task_to_proto_without_plan(self, sample_task_without_plan):
        """Test _task_to_proto with task without plan_id."""
        proto_task = ResponseMapper._task_to_proto(sample_task_without_plan)

        assert proto_task.task_id == "T-002"
        assert proto_task.story_id == "STORY-002"
        assert proto_task.plan_id == ""  # Empty string when None
        assert proto_task.title == "Ad-hoc Task"
        assert proto_task.description == "Task without plan"
        assert proto_task.type == "bug_fix"
        assert proto_task.status == "in_progress"

    def test_task_to_proto_all_task_types(self):
        """Test _task_to_proto with different task types."""
        now = datetime.now(UTC)
        for task_type in [TaskType.DEVELOPMENT, TaskType.TESTING, TaskType.REFACTOR, TaskType.BUG_FIX]:
            task = Task(
                task_id=TaskId(f"T-{task_type.value}"),
                story_id=StoryId("STORY-001"),
                plan_id=None,
                title=f"Task {task_type.value}",
                description="",
                type=task_type,
                status=TaskStatus.TODO,
                created_at=now,
                updated_at=now,
            )
            proto_task = ResponseMapper._task_to_proto(task)
            assert proto_task.type == task_type.value

    def test_task_to_proto_all_task_statuses(self):
        """Test _task_to_proto with different task statuses."""
        now = datetime.now(UTC)
        for status in [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
            TaskStatus.BLOCKED,
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        ]:
            task = Task(
                task_id=TaskId(f"T-{status.value}"),
                story_id=StoryId("STORY-001"),
                plan_id=None,
                title=f"Task {status.value}",
                description="",
                type=TaskType.DEVELOPMENT,
                status=status,
                created_at=now,
                updated_at=now,
            )
            proto_task = ResponseMapper._task_to_proto(task)
            assert proto_task.status == status.value

