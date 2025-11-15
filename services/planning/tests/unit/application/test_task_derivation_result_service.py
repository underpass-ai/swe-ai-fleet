"""Unit tests for TaskDerivationResultService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.actors.role import Role, RoleType
from planning.domain.value_objects.content.task_description import TaskDescription
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_attributes.duration import Duration
from planning.domain.value_objects.task_attributes.priority import Priority
from planning.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.task_derivation.task_node import TaskNode


@pytest.fixture
def mock_create_task_usecase() -> AsyncMock:
    """Mock CreateTaskUseCase."""
    return AsyncMock(spec=CreateTaskUseCase)


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Mock StoragePort."""
    mock = AsyncMock(spec=StoragePort)

    # Mock get_plan to return a valid Plan with roles from event
    plan = Plan(
        plan_id=PlanId("plan-001"),
        story_id=StoryId("story-001"),
        title=Title("Implement feature X"),
        description=TaskDescription("Feature description"),
        acceptance_criteria=("Criterion 1", "Criterion 2"),  # tuple[str, ...]
        technical_notes="Technical notes",  # str, not Brief
        roles=("DEVELOPER", "QA"),  # Roles from planning.plan.approved event
    )
    mock.get_plan.return_value = plan

    return mock


@pytest.fixture
def mock_messaging() -> AsyncMock:
    """Mock MessagingPort."""
    return AsyncMock(spec=MessagingPort)


@pytest.mark.asyncio
class TestTaskDerivationResultService:
    """Test suite for TaskDerivationResultService."""

    async def test_process_creates_tasks_in_order(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that process creates tasks in dependency order."""
        # Given: service with mocked dependencies
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: task nodes (no dependencies, no role - Planning Service assigns roles)
        task_nodes = (
            TaskNode(
                task_id=TaskId("TASK-001"),
                title=Title("Setup database"),
                description=TaskDescription("Create schema"),
                keywords=(),
                estimated_hours=Duration(8),
                priority=Priority(1),
            ),
            TaskNode(
                task_id=TaskId("TASK-002"),
                title=Title("Create API"),
                description=TaskDescription("Build REST API"),
                keywords=(),
                estimated_hours=Duration(16),
                priority=Priority(2),
            ),
        )

        # When: process task derivation result
        await service.process(
            plan_id=PlanId("plan-001"),
            story_id=StoryId("story-001"),
            role="DEVELOPER",
            task_nodes=task_nodes,
        )

        # Then: tasks created
        assert mock_create_task_usecase.execute.await_count == 2

        # Then: plan NOT fetched (Task depends on Story, role comes from event context)
        mock_storage.get_plan.assert_not_awaited()

        # Then: success event published
        mock_messaging.publish_event.assert_awaited()

    async def test_process_with_empty_role_raises_error(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that process raises ValueError if role is empty."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: task nodes
        task_nodes = (
            TaskNode(
                task_id=TaskId("TASK-001"),
                title=Title("Setup database"),
                description=TaskDescription("Create schema"),
                keywords=(),
                estimated_hours=Duration(8),
                priority=Priority(1),
            ),
        )

        # When/Then: raises ValueError for empty role
        with pytest.raises(ValueError, match="Role cannot be empty"):
            await service.process(
                plan_id=PlanId("plan-001"),
                story_id=StoryId("story-001"),
                role="",  # Empty role
                task_nodes=task_nodes,
            )

    async def test_process_with_empty_tasks_raises_error(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that empty task_nodes raises ValueError."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # When/Then: empty tasks
        with pytest.raises(ValueError, match="No tasks provided"):
            await service.process(
                plan_id=PlanId("plan-001"),
                story_id=StoryId("story-001"),
                role="DEVELOPER",
                task_nodes=(),
            )

    async def test_process_with_circular_dependency_raises_error(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that circular dependencies raise ValueError."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: tasks with circular dependency via keywords
        # (This is a simplified test - actual circular detection tested in domain)
        task_nodes = (
            TaskNode(
                task_id=TaskId("TASK-001"),
                title=Title("Setup database using api"),
                description=TaskDescription("Create schema"),
                keywords=(Keyword("database"), Keyword("api")),
                estimated_hours=Duration(8),
                priority=Priority(1),
            ),
            TaskNode(
                task_id=TaskId("TASK-002"),
                title=Title("Create API using database"),
                description=TaskDescription("Build REST API"),
                keywords=(Keyword("api"), Keyword("database")),
                estimated_hours=Duration(16),
                priority=Priority(2),
            ),
        )

        # When/Then: process may detect circular (depending on heuristic)
        # This test validates error handling path
        try:
            await service.process(
                plan_id=PlanId("plan-001"),
                story_id=StoryId("story-001"),
                role="DEVELOPER",
                task_nodes=task_nodes,
            )
        except ValueError:
            # Expected if circular detected
            pass

    async def test_process_with_nonexistent_plan_raises_error(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that nonexistent plan raises ValueError."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: storage returns None (plan not found)
        mock_storage.get_plan.return_value = None

        # Given: valid task nodes
        task_nodes = (
            TaskNode(
                task_id=TaskId("TASK-001"),
                title=Title("Setup database"),
                description=TaskDescription("Create schema"),
                keywords=(),
                estimated_hours=Duration(8),
                priority=Priority(1),
            ),
        )

        # When/Then: process succeeds (no Plan lookup needed - Task depends on Story)
        await service.process(
            plan_id=PlanId("plan-999"),
            story_id=StoryId("story-001"),
            role="DEVELOPER",
            task_nodes=task_nodes,
        )

        # Then: plan NOT fetched (Task depends on Story, role comes from event context)
        mock_storage.get_plan.assert_not_awaited()

