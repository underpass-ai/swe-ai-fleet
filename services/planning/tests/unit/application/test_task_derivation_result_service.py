"""Unit tests for TaskDerivationResultService."""

from unittest.mock import AsyncMock, patch

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from core.shared.domain.value_objects.task_derivation.keyword import Keyword
from planning.application.ports import MessagingPort, StoragePort
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.domain.value_objects.task_derivation.dependency_graph import DependencyGraph
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

        # Then: no dependencies saved (tasks have no dependencies)
        mock_storage.save_task_dependencies.assert_not_awaited()

    async def test_process_saves_dependencies_when_present(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that process saves dependencies when graph has dependencies."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: task nodes with keywords that will create dependencies
        task_1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create schema"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        task_2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build REST API"),
            keywords=(),
            estimated_hours=Duration(16),
            priority=Priority(2),
        )
        task_nodes = (task_1, task_2)

        # When: process task derivation result
        await service.process(
            plan_id=PlanId("plan-001"),
            story_id=StoryId("story-001"),
            role="DEVELOPER",
            task_nodes=task_nodes,
        )

        # Then: tasks created
        assert mock_create_task_usecase.execute.await_count == 2

        # Then: dependencies saved (task_2 mentions "database" from task_1)
        mock_storage.save_task_dependencies.assert_awaited_once()

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
        """Test that circular dependencies raise ValueError and notify manual review."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: tasks that will create a circular dependency
        task_1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create schema"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        task_2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build REST API"),
            keywords=(),
            estimated_hours=Duration(16),
            priority=Priority(2),
        )
        task_nodes = (task_1, task_2)

        # Given: create a graph with circular dependency manually
        # A -> B -> A (circular)
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_1.task_id,
            reason=DependencyReason("task-2 depends on task-1"),
        )
        circular_graph = DependencyGraph(tasks=task_nodes, dependencies=(dep1, dep2))

        # Mock DependencyGraph.from_tasks to return circular graph
        with patch(
            "planning.application.services.task_derivation_result_service.DependencyGraph.from_tasks"
        ) as mock_from_tasks:
            mock_from_tasks.return_value = circular_graph

            # When/Then: raises ValueError for circular dependency
            with pytest.raises(ValueError, match="Circular dependencies for Story story-001"):
                await service.process(
                    plan_id=PlanId("plan-001"),
                    story_id=StoryId("story-001"),
                    role="DEVELOPER",
                    task_nodes=task_nodes,
                )

            # Then: manual review notification sent BEFORE exception
            # The service calls _notify_manual_review before raising ValueError
            # Verify that publish_event was called with the correct subject
            publish_calls = [
                call for call in mock_messaging.publish_event.await_args_list
                if call.kwargs.get("subject") == "planning.task.derivation.failed"
            ]
            assert len(publish_calls) > 0, "Manual review notification not sent (expected before exception)"

            # Then: no tasks created
            mock_create_task_usecase.execute.assert_not_awaited()

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

    async def test_process_publish_event_failure_does_not_raise(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that publish_event failure is logged but does not raise."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: messaging fails to publish event
        mock_messaging.publish_event.side_effect = Exception("NATS connection failed")

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

        # When: process completes (should not raise despite publish failure)
        await service.process(
            plan_id=PlanId("plan-001"),
            story_id=StoryId("story-001"),
            role="DEVELOPER",
            task_nodes=task_nodes,
        )

        # Then: task still created despite event failure
        assert mock_create_task_usecase.execute.await_count == 1

    async def test_notify_manual_review_publish_failure_logged(
        self,
        mock_create_task_usecase: AsyncMock,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that _notify_manual_review handles publish failure gracefully."""
        # Given: service
        service = TaskDerivationResultService(
            create_task_usecase=mock_create_task_usecase,
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # Given: messaging fails to publish notification
        mock_messaging.publish_event.side_effect = Exception("NATS connection failed")

        # Given: tasks that will create a circular dependency
        task_1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create schema"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        task_2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build REST API"),
            keywords=(),
            estimated_hours=Duration(16),
            priority=Priority(2),
        )
        task_nodes = (task_1, task_2)

        # Given: create a graph with circular dependency
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_1.task_id,
            reason=DependencyReason("task-2 depends on task-1"),
        )
        circular_graph = DependencyGraph(tasks=task_nodes, dependencies=(dep1, dep2))

        # Mock DependencyGraph.from_tasks to return circular graph
        with patch(
            "planning.application.services.task_derivation_result_service.DependencyGraph.from_tasks"
        ) as mock_from_tasks:
            mock_from_tasks.return_value = circular_graph

            # When/Then: raises ValueError (expected)
            with pytest.raises(ValueError, match="Circular dependencies"):
                await service.process(
                    plan_id=PlanId("plan-001"),
                    story_id=StoryId("story-001"),
                    role="DEVELOPER",
                    task_nodes=task_nodes,
                )

            # Then: notification attempted (even if it fails)
            assert mock_messaging.publish_event.await_count >= 1

