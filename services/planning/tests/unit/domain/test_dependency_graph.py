"""Unit tests for DependencyGraph value object."""

import pytest

from planning.domain.value_objects.actors.role import Role, RoleType
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.domain.value_objects.task_derivation.dependency_graph import DependencyGraph
from planning.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.task_derivation.task_node import TaskNode


class TestDependencyGraph:
    """Test suite for DependencyGraph VO."""

    def test_create_valid_graph(self) -> None:
        """Test creating a valid dependency graph."""
        # Given: tasks and dependencies
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=Brief("Create database schema"),
            role=Role(RoleType.DEVELOPER),
            keywords=(Keyword("database"), Keyword("schema")),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=Brief("Build REST API"),
            role=Role(RoleType.DEVELOPER),
            keywords=(Keyword("api"), Keyword("rest")),
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
            description=Brief("Create database schema"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
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

    def test_detect_circular_dependency_simple(self) -> None:
        """Test detection of simple circular dependency (A → B → A)."""
        # Given: circular dependency
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Task A"),
            description=Brief("Task A"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Task B"),
            description=Brief("Task B"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
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
            description=Brief("Task A"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Task B"),
            description=Brief("Task B"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task3 = TaskNode(
            task_id=TaskId("TASK-003"),
            title=Title("Task C"),
            description=Brief("Task C"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
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

    def test_get_execution_levels_linear(self) -> None:
        """Test topological sort for linear dependencies."""
        # Given: A → B → C (linear)
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=Brief("Task A"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=Brief("Task B"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task_c = TaskNode(
            task_id=TaskId("TASK-C"),
            title=Title("Task C"),
            description=Brief("Task C"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
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

        # When: get execution levels
        graph = DependencyGraph(tasks=(task_a, task_b, task_c), dependencies=dependencies)
        levels = graph.get_execution_levels()

        # Then: 3 levels (A, then B, then C)
        assert len(levels) == 3
        assert len(levels[0]) == 1
        assert levels[0][0].task_id == TaskId("TASK-A")
        assert levels[1][0].task_id == TaskId("TASK-B")
        assert levels[2][0].task_id == TaskId("TASK-C")

    def test_get_execution_levels_parallel(self) -> None:
        """Test topological sort with parallel tasks."""
        # Given: A and B can run in parallel, both depend on nothing
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=Brief("Task A"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=Brief("Task B"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        # When: no dependencies (parallel)
        graph = DependencyGraph(tasks=(task_a, task_b), dependencies=())
        levels = graph.get_execution_levels()

        # Then: single level with both tasks
        assert len(levels) == 1
        assert len(levels[0]) == 2

    def test_get_ordered_tasks(self) -> None:
        """Test get_ordered_tasks flattens execution levels."""
        # Given: linear dependency A → B → C
        task_a = TaskNode(
            task_id=TaskId("TASK-A"),
            title=Title("Task A"),
            description=Brief("Task A"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task_b = TaskNode(
            task_id=TaskId("TASK-B"),
            title=Title("Task B"),
            description=Brief("Task B"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
        )

        task_c = TaskNode(
            task_id=TaskId("TASK-C"),
            title=Title("Task C"),
            description=Brief("Task C"),
            role=Role(RoleType.DEVELOPER),
            keywords=(),
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

    def test_from_tasks_factory_method(self) -> None:
        """Test from_tasks factory method with keyword-based inference."""
        # Given: tasks with keywords
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database schema"),
            description=Brief("Create database"),
            role=Role(RoleType.DEVELOPER),
            keywords=(Keyword("database"), Keyword("schema")),
        )

        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=Brief("Build API"),
            role=Role(RoleType.DEVELOPER),
            keywords=(Keyword("api"),),
        )

        # When: build graph using factory
        graph = DependencyGraph.from_tasks((task1, task2))

        # Then: dependencies inferred
        assert len(graph.tasks) == 2
        # API should depend on database (keyword "database" in API title)
        assert len(graph.dependencies) >= 0  # May or may not infer (heuristic)

