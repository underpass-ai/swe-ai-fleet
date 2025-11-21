"""Unit tests for DependencyGraph value object."""

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from core.shared.domain.value_objects.task_derivation.keyword import Keyword

from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.domain.value_objects.task_derivation.dependency_graph import DependencyGraph
from planning.domain.value_objects.task_derivation.task_node import TaskNode


@pytest.fixture
def task_1() -> TaskNode:
    """Create task 1."""
    return TaskNode(
        task_id=TaskId("task-1"),
        title=Title("Task 1"),
        description=TaskDescription("First task"),
        keywords=(),
        estimated_hours=Duration(4),
        priority=Priority(1),
    )


@pytest.fixture
def task_2() -> TaskNode:
    """Create task 2."""
    return TaskNode(
        task_id=TaskId("task-2"),
        title=Title("Task 2"),
        description=TaskDescription("Second task"),
        keywords=(),
        estimated_hours=Duration(6),
        priority=Priority(2),
    )


@pytest.fixture
def task_3() -> TaskNode:
    """Create task 3."""
    return TaskNode(
        task_id=TaskId("task-3"),
        title=Title("Task 3"),
        description=TaskDescription("Third task"),
        keywords=(),
        estimated_hours=Duration(2),
        priority=Priority(3),
    )


class TestDependencyGraphValidation:
    """Tests for DependencyGraph validation."""

    def test_empty_tasks_raises_error(self) -> None:
        """Test that empty tasks raise ValueError."""
        with pytest.raises(ValueError, match="tasks cannot be empty"):
            DependencyGraph(tasks=(), dependencies=())

    def test_invalid_dependency_from_reference_raises_error(
        self, task_1: TaskNode
    ) -> None:
        """Test that dependency referencing unknown 'from' task raises error."""
        invalid_dep = DependencyEdge(
            from_task_id=TaskId("unknown-task"),
            to_task_id=task_1.task_id,
            reason=DependencyReason("test"),
        )
        with pytest.raises(ValueError, match="Dependency references unknown task"):
            DependencyGraph(tasks=(task_1,), dependencies=(invalid_dep,))

    def test_invalid_dependency_to_reference_raises_error(
        self, task_1: TaskNode
    ) -> None:
        """Test that dependency referencing unknown 'to' task raises error."""
        invalid_dep = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=TaskId("unknown-task"),
            reason=DependencyReason("test"),
        )
        with pytest.raises(ValueError, match="Dependency references unknown task"):
            DependencyGraph(tasks=(task_1,), dependencies=(invalid_dep,))

    def test_valid_graph_creates_successfully(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that valid graph creates successfully."""
        dependency = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dependency,))
        assert graph.tasks == (task_1, task_2)
        assert graph.dependencies == (dependency,)


class TestHasCircularDependency:
    """Tests for has_circular_dependency method."""

    def test_no_circular_dependency_returns_false(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that graph without cycles returns False."""
        dependency = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dependency,))
        assert not graph.has_circular_dependency()

    def test_simple_circular_dependency_returns_true(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that simple circular dependency (A→B→A) returns True."""
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
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dep1, dep2))
        assert graph.has_circular_dependency()

    def test_complex_circular_dependency_returns_true(
        self, task_1: TaskNode, task_2: TaskNode, task_3: TaskNode
    ) -> None:
        """Test that complex circular dependency (A→B→C→A) returns True."""
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_3.task_id,
            reason=DependencyReason("task-2 depends on task-3"),
        )
        dep3 = DependencyEdge(
            from_task_id=task_3.task_id,
            to_task_id=task_1.task_id,
            reason=DependencyReason("task-3 depends on task-1"),
        )
        graph = DependencyGraph(
            tasks=(task_1, task_2, task_3), dependencies=(dep1, dep2, dep3)
        )
        assert graph.has_circular_dependency()

    def test_no_dependencies_no_circular(self, task_1: TaskNode) -> None:
        """Test that graph with no dependencies has no cycles."""
        graph = DependencyGraph(tasks=(task_1,), dependencies=())
        assert not graph.has_circular_dependency()


class TestGetRootTasks:
    """Tests for get_root_tasks method."""

    def test_single_task_no_dependencies_returns_task(
        self, task_1: TaskNode
    ) -> None:
        """Test that single task with no dependencies is returned."""
        graph = DependencyGraph(tasks=(task_1,), dependencies=())
        root_tasks = graph.get_root_tasks()
        assert root_tasks == (task_1,)

    def test_multiple_tasks_no_dependencies_returns_all(
        self, task_1: TaskNode, task_2: TaskNode, task_3: TaskNode
    ) -> None:
        """Test that all tasks with no dependencies are returned."""
        graph = DependencyGraph(tasks=(task_1, task_2, task_3), dependencies=())
        root_tasks = graph.get_root_tasks()
        assert len(root_tasks) == 3
        assert task_1 in root_tasks
        assert task_2 in root_tasks
        assert task_3 in root_tasks

    def test_tasks_with_dependencies_excludes_dependents(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that tasks with incoming dependencies are excluded."""
        # task-1 depends on task-2, so task-2 has incoming dependency
        dependency = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dependency,))
        root_tasks = graph.get_root_tasks()
        assert len(root_tasks) == 1
        # task-1 has no incoming dependencies, so it's the root
        assert task_1 in root_tasks
        # task-2 has incoming dependency from task-1, so it's not a root
        assert task_2 not in root_tasks


class TestGetExecutionLevels:
    """Tests for get_execution_levels method."""

    def test_single_task_returns_single_level(self, task_1: TaskNode) -> None:
        """Test that single task returns single level."""
        graph = DependencyGraph(tasks=(task_1,), dependencies=())
        levels = graph.get_execution_levels()
        assert len(levels) == 1
        assert levels[0] == (task_1,)

    def test_linear_dependencies_returns_ordered_levels(
        self, task_1: TaskNode, task_2: TaskNode, task_3: TaskNode
    ) -> None:
        """Test that linear dependencies return correct levels."""
        # task-1 depends on task-2, task-2 depends on task-3
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_3.task_id,
            reason=DependencyReason("task-2 depends on task-3"),
        )
        graph = DependencyGraph(
            tasks=(task_1, task_2, task_3), dependencies=(dep1, dep2)
        )
        levels = graph.get_execution_levels()
        assert len(levels) == 3
        assert task_3 in levels[0]  # Level 0: task-3 (no dependencies)
        assert task_2 in levels[1]  # Level 1: task-2 (depends on task-3)
        assert task_1 in levels[2]  # Level 2: task-1 (depends on task-2)

    def test_parallel_dependencies_returns_same_level(
        self, task_1: TaskNode, task_2: TaskNode, task_3: TaskNode
    ) -> None:
        """Test that parallel dependencies are in same level."""
        # Both task-1 and task-2 depend on task-3
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_3.task_id,
            reason=DependencyReason("task-1 depends on task-3"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_3.task_id,
            reason=DependencyReason("task-2 depends on task-3"),
        )
        graph = DependencyGraph(
            tasks=(task_1, task_2, task_3), dependencies=(dep1, dep2)
        )
        levels = graph.get_execution_levels()
        assert len(levels) == 2
        assert task_3 in levels[0]  # Level 0: task-3
        assert task_1 in levels[1] and task_2 in levels[1]  # Level 1: both

    def test_circular_dependency_raises_error(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that circular dependency raises ValueError."""
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
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dep1, dep2))
        with pytest.raises(ValueError, match="circular dependencies"):
            graph.get_execution_levels()


class TestGetOrderedTasks:
    """Tests for get_ordered_tasks method."""

    def test_single_task_returns_single_task(self, task_1: TaskNode) -> None:
        """Test that single task returns single task."""
        graph = DependencyGraph(tasks=(task_1,), dependencies=())
        ordered = graph.get_ordered_tasks()
        assert ordered == (task_1,)

    def test_linear_dependencies_returns_ordered_sequence(
        self, task_1: TaskNode, task_2: TaskNode, task_3: TaskNode
    ) -> None:
        """Test that linear dependencies return ordered sequence."""
        dep1 = DependencyEdge(
            from_task_id=task_1.task_id,
            to_task_id=task_2.task_id,
            reason=DependencyReason("task-1 depends on task-2"),
        )
        dep2 = DependencyEdge(
            from_task_id=task_2.task_id,
            to_task_id=task_3.task_id,
            reason=DependencyReason("task-2 depends on task-3"),
        )
        graph = DependencyGraph(
            tasks=(task_1, task_2, task_3), dependencies=(dep1, dep2)
        )
        ordered = graph.get_ordered_tasks()
        assert len(ordered) == 3
        # task-3 should come before task-2, task-2 before task-1
        assert ordered.index(task_3) < ordered.index(task_2)
        assert ordered.index(task_2) < ordered.index(task_1)

    def test_circular_dependency_raises_error(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that circular dependency raises ValueError."""
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
        graph = DependencyGraph(tasks=(task_1, task_2), dependencies=(dep1, dep2))
        with pytest.raises(ValueError, match="circular dependencies"):
            graph.get_ordered_tasks()


class TestFromTasks:
    """Tests for from_tasks factory method."""

    def test_empty_tasks_raises_error(self) -> None:
        """Test that empty tasks raise ValueError."""
        with pytest.raises(ValueError, match="tasks cannot be empty"):
            DependencyGraph.from_tasks(())

    def test_single_task_creates_graph_with_no_dependencies(
        self, task_1: TaskNode
    ) -> None:
        """Test that single task creates graph with no dependencies."""
        graph = DependencyGraph.from_tasks((task_1,))
        assert graph.tasks == (task_1,)
        assert graph.dependencies == ()

    def test_tasks_with_keyword_matches_creates_dependencies(self) -> None:
        """Test that tasks with keyword matches create dependencies."""
        task_a = TaskNode(
            task_id=TaskId("task-a"),
            title=Title("Create database schema"),
            description=TaskDescription("Create schema"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("task-b"),
            title=Title("Connect to database"),
            description=TaskDescription("Connect to database"),
            keywords=(),
            estimated_hours=Duration(2),
            priority=Priority(2),
        )
        graph = DependencyGraph.from_tasks((task_a, task_b))
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].from_task_id.value == "task-b"
        assert graph.dependencies[0].to_task_id.value == "task-a"

    def test_tasks_without_keyword_matches_no_dependencies(
        self, task_1: TaskNode, task_2: TaskNode
    ) -> None:
        """Test that tasks without keyword matches create no dependencies."""
        graph = DependencyGraph.from_tasks((task_1, task_2))
        assert graph.tasks == (task_1, task_2)
        assert graph.dependencies == ()

