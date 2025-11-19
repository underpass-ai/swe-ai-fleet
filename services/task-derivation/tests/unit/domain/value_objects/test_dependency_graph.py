"""Unit tests for DependencyGraph value object."""

import pytest

from task_derivation.domain.value_objects.content.dependency_reason import DependencyReason

# Role removed from TaskNode - Task Derivation Service assigns roles downstream
from core.shared.domain.value_objects.content.task_description import TaskDescription
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_graph import (
    DependencyGraph,
)
from core.shared.domain.value_objects.task_derivation.keyword import (
    Keyword,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


class TestDependencyGraph:
    """Test suite for DependencyGraph VO."""

    def test_create_valid_graph(self) -> None:
        """Test creating a valid dependency graph."""
        # Given: tasks and dependencies
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database schema"),
            keywords=(Keyword("database"), Keyword("schema")),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build REST API"),
            keywords=(Keyword("api"), Keyword("rest")),
            estimated_hours=Duration(16),
            priority=Priority(2),
        )

        dependency = DependencyEdge(
            from_task_id=TaskId("TASK-002"),
            to_task_id=TaskId("TASK-001"),
            reason=DependencyReason("API needs database"),
        )

        # When: create graph
        graph = DependencyGraph(
            tasks=(task1, task2),
            dependencies=(dependency,),
        )

        # Then: graph is valid
        assert len(graph.tasks) == 2
        assert len(graph.dependencies) == 1
        assert not graph.has_circular_dependency()

    def test_empty_tasks_raises_error(self) -> None:
        """Test that empty tasks raises ValueError."""
        # When/Then: empty tasks
        with pytest.raises(ValueError, match="tasks cannot be empty"):
            DependencyGraph(tasks=(), dependencies=())

    def test_invalid_dependency_reference_raises_error(self) -> None:
        """Test that dependency referencing non-existent task raises error."""
        # Given: task and dependency to non-existent task
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database schema"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        dependency = DependencyEdge(
            from_task_id=TaskId("TASK-001"),
            to_task_id=TaskId("TASK-999"),  # Non-existent
            reason=DependencyReason("Invalid reference"),
        )

        # When/Then: invalid reference
        with pytest.raises(ValueError, match="TASK-999"):
            DependencyGraph(
                tasks=(task1,),
                dependencies=(dependency,),
            )

    def test_invalid_dependency_from_reference_raises_error(self) -> None:
        """Dependencies referencing unknown source tasks fail fast."""
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database schema"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        dependency = DependencyEdge(
            from_task_id=TaskId("TASK-999"),
            to_task_id=TaskId("TASK-001"),
            reason=DependencyReason("Invalid reference"),
        )

        with pytest.raises(ValueError, match="TASK-999"):
            DependencyGraph(tasks=(task1,), dependencies=(dependency,))

    def test_detect_circular_dependency_simple(self) -> None:
        """Test detection of simple circular dependency (A → B → A)."""
        # Given: circular dependency
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        dependencies = (
            DependencyEdge(
                from_task_id=TaskId("TASK-001"),
                to_task_id=TaskId("TASK-002"),
                reason=DependencyReason("A depends on B"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-002"),
                to_task_id=TaskId("TASK-001"),
                reason=DependencyReason("B depends on A"),
            ),
        )

        # When: create graph
        graph = DependencyGraph(tasks=(task1, task2), dependencies=dependencies)

        # Then: circular dependency detected
        assert graph.has_circular_dependency()

    def test_detect_circular_dependency_complex(self) -> None:
        """Test detection of complex circular dependency (A → B → C → A)."""
        # Given: complex circular dependency
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task3 = TaskNode(
            task_id=TaskId("TASK-003"),
            title=Title("Task C"),
            description=TaskDescription("Task C"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        dependencies = (
            DependencyEdge(
                from_task_id=TaskId("TASK-001"),
                to_task_id=TaskId("TASK-002"),
                reason=DependencyReason("A → B"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-002"),
                to_task_id=TaskId("TASK-003"),
                reason=DependencyReason("B → C"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-003"),
                to_task_id=TaskId("TASK-001"),
                reason=DependencyReason("C → A"),
            ),
        )

        # When: create graph
        graph = DependencyGraph(tasks=(task1, task2, task3), dependencies=dependencies)

        # Then: circular dependency detected
        assert graph.has_circular_dependency()

    def test_get_execution_plan_linear(self) -> None:
        """Test topological sort for linear dependencies."""
        # Given: A → B → C (linear)
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task_c = TaskNode(
            task_id=TaskId("TASK-C"),
            title=Title("Task C"),
            description=TaskDescription("Task C"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        dependencies = (
            DependencyEdge(
                from_task_id=TaskId("TASK-B"),
                to_task_id=TaskId("TASK-A"),
                reason=DependencyReason("B depends on A"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-C"),
                to_task_id=TaskId("TASK-B"),
                reason=DependencyReason("C depends on B"),
            ),
        )

        # When: build execution plan
        graph = DependencyGraph(tasks=(task_a, task_b, task_c), dependencies=dependencies)
        plan = graph.get_execution_plan()

        # Then: sequential order A, B, C
        assert len(plan.steps) == 3
        assert plan.steps[0].task.task_id == TaskId("TASK-A")
        assert plan.steps[1].task.task_id == TaskId("TASK-B")
        assert plan.steps[2].task.task_id == TaskId("TASK-C")

    def test_get_execution_plan_without_dependencies(self) -> None:
        """Tasks without dependencies are ordered deterministically."""
        # Given: A and B can run in parallel, both depend on nothing
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: no dependencies
        graph = DependencyGraph(tasks=(task_a, task_b), dependencies=())
        plan = graph.get_execution_plan()

        # Then: both tasks scheduled
        assert len(plan.steps) == 2
        assert {step.task.task_id for step in plan.steps} == {TaskId("TASK-A"), TaskId("TASK-B")}

    def test_get_root_tasks(self) -> None:
        """Ensure root tasks contain nodes without inbound edges."""
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        dependency = DependencyEdge(
            from_task_id=task_b.task_id,
            to_task_id=task_a.task_id,
            reason=DependencyReason("B depends on A"),
        )

        graph = DependencyGraph(tasks=(task_a, task_b), dependencies=(dependency,))

        roots = graph.get_root_tasks()

        assert len(roots) == 1
        assert roots[0].task_id == TaskId("TASK-B")

    def test_get_ordered_tasks(self) -> None:
        """Test get_ordered_tasks flattens execution levels."""
        # Given: linear dependency A → B → C
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        task_c = TaskNode(
            task_id=TaskId("TASK-C"),
            title=Title("Task C"),
            description=TaskDescription("Task C"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        dependencies = (
            DependencyEdge(
                from_task_id=TaskId("TASK-B"),
                to_task_id=TaskId("TASK-A"),
                reason=DependencyReason("B depends on A"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-C"),
                to_task_id=TaskId("TASK-B"),
                reason=DependencyReason("C depends on B"),
            ),
        )

        # When: get ordered tasks
        graph = DependencyGraph(tasks=(task_a, task_b, task_c), dependencies=dependencies)
        ordered = graph.get_ordered_tasks()

        # Then: flattened in order A, B, C
        assert len(ordered) == 3
        assert ordered[0].task_id == TaskId("TASK-A")
        assert ordered[1].task_id == TaskId("TASK-B")
        assert ordered[2].task_id == TaskId("TASK-C")

    def test_get_execution_plan_raises_on_circular_dependencies(self) -> None:
        """Ensure get_execution_plan fails if graph has cycles."""
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=TaskDescription("Task A"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=TaskDescription("Task B"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        dependencies = (
            DependencyEdge(
                from_task_id=TaskId("TASK-A"),
                to_task_id=TaskId("TASK-B"),
                reason=DependencyReason("A depends on B"),
            ),
            DependencyEdge(
                from_task_id=TaskId("TASK-B"),
                to_task_id=TaskId("TASK-A"),
                reason=DependencyReason("B depends on A"),
            ),
        )

        graph = DependencyGraph(tasks=(task_a, task_b), dependencies=dependencies)

        with pytest.raises(ValueError, match="contains circular dependencies"):
            graph.get_execution_plan()

    def test_from_tasks_factory_method(self) -> None:
        """Test from_tasks factory method with keyword-based inference."""
        # Given: tasks with keywords
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database schema"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"), Keyword("schema")),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(16),
            priority=Priority(2),
        )

        # When: build graph using factory
        graph = DependencyGraph.from_tasks((task1, task2))

        # Then: dependencies inferred
        assert len(graph.tasks) == 2
        assert len(graph.dependencies) >= 1

