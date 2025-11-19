"""DependencyGraph value object with business logic.

Value Object (DDD):
- Defined by its values, not identity
- Immutable (frozen=True)
- Contains domain logic (Tell, Don't Ask)
- Factory methods for construction
"""

from __future__ import annotations

from dataclasses import dataclass

from task_derivation.domain.value_objects.content.dependency_reason import (
    DependencyReason,
)

from .dependency_edge import DependencyEdge
from .execution_plan import ExecutionPlan
from .execution_step import ExecutionStep
from .task_node import TaskNode
from .topology_node import TopologyNode
from .topology_state import TopologyState


class DependencyInferenceHelper:
    """Helper class for dependency inference logic.

    Encapsulates static methods for inferring dependencies between tasks.
    Separates inference logic from graph structure.
    """

    @staticmethod
    def infer_dependencies_from_keywords(
        tasks: tuple[TaskNode, ...]
    ) -> tuple[DependencyEdge, ...]:
        """Infer dependencies based on keyword matching.

        Private method: Business logic for dependency inference.
        Simple heuristic: If task B mentions task A's keywords,
        then B likely depends on A.

        Tell, Don't Ask: Uses TaskNode behavior for matching.

        Args:
            tasks: Tuple of task nodes to analyze

        Returns:
            Tuple of inferred dependency edges
        """
        dependencies: list[DependencyEdge] = []

        for i, task_a in enumerate(tasks):
            for task_b in tasks[i + 1:]:
                # Check bidirectional keyword matching
                dep = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)
                if dep:
                    dependencies.append(dep)

        return tuple(dependencies)

    @staticmethod
    def find_dependency_between_tasks(
        task_a: TaskNode, task_b: TaskNode
    ) -> DependencyEdge | None:
        """Find dependency between two tasks based on keyword matching.

        Args:
            task_a: First task to check
            task_b: Second task to check

        Returns:
            DependencyEdge if dependency found, None otherwise
        """
        # Check if task_b mentions task_a's keywords
        dep = DependencyInferenceHelper.check_keyword_match(
            source_task=task_b, target_task=task_a, target_keywords=task_a.keywords
        )
        if dep:
            return dep

        # Check if task_a mentions task_b's keywords
        dep = DependencyInferenceHelper.check_keyword_match(
            source_task=task_a, target_task=task_b, target_keywords=task_b.keywords
        )
        if dep:
            return dep

        return None

    @staticmethod
    def check_keyword_match(
        source_task: TaskNode, target_task: TaskNode, target_keywords: tuple
    ) -> DependencyEdge | None:
        """Check if source task mentions any of target task's keywords.

        Args:
            source_task: Task to check for keyword mentions
            target_task: Task providing keywords
            target_keywords: Keywords from target task

        Returns:
            DependencyEdge if match found, None otherwise
        """
        for keyword in target_keywords:
            if keyword.matches_in(str(source_task.title)):
                return DependencyEdge(
                    from_task_id=source_task.task_id,
                    to_task_id=target_task.task_id,
                    reason=DependencyReason(
                        f"Task references '{keyword}' from prerequisite"
                    ),
                )
        return None


@dataclass(frozen=True)
class DependencyGraph:
    """Dependency graph with tasks and their relationships.

    Immutable result of dependency analysis.
    Contains tasks and their dependency relationships.
    NO serialization methods (use mappers in infrastructure).

    Following DDD:
    - Value object with rich behavior
    - Immutable
    - Fail-fast validation
    - Tell, Don't Ask: graph knows how to analyze itself
    """

    tasks: tuple[TaskNode, ...]
    dependencies: tuple[DependencyEdge, ...]

    def __post_init__(self) -> None:
        """Validate dependency graph (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.tasks:
            raise ValueError("tasks cannot be empty")

        # Validate that all dependencies reference existing tasks
        task_ids = {task.task_id.value for task in self.tasks}
        for dep in self.dependencies:
            if dep.from_task_id.value not in task_ids:
                raise ValueError(
                    f"Dependency references unknown task: {dep.from_task_id.value}"
                )
            if dep.to_task_id.value not in task_ids:
                raise ValueError(
                    f"Dependency references unknown task: {dep.to_task_id.value}"
                )

    def has_circular_dependency(self) -> bool:
        """Check if graph contains circular dependencies.

        Tell, Don't Ask: Graph knows how to validate itself.

        Returns:
            True if circular dependency detected
        """
        graph = self._build_adjacency_list()
        visited: set[str] = set()
        rec_stack: set[str] = set()

        for task in self.tasks:
            task_id = task.task_id.value
            if task_id not in visited:
                if self._has_cycle_in_subgraph(graph, task_id, visited, rec_stack):
                    return True

        return False

    def _build_adjacency_list(self) -> dict[str, list[str]]:
        """Build adjacency list representation of the graph.

        Returns:
            Dictionary mapping task_id to list of dependent task_ids
        """
        graph: dict[str, list[str]] = {task.task_id.value: [] for task in self.tasks}
        for dep in self.dependencies:
            graph[dep.from_task_id.value].append(dep.to_task_id.value)
        return graph

    def _has_cycle_in_subgraph(
        self, graph: dict[str, list[str]], node: str, visited: set[str], rec_stack: set[str]
    ) -> bool:
        """Check if subgraph starting from node contains a cycle (DFS).

        Args:
            graph: Adjacency list representation
            node: Current node to check
            visited: Set of visited nodes
            rec_stack: Set of nodes in current recursion stack

        Returns:
            True if cycle detected
        """
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if self._has_cycle_in_subgraph(graph, neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    def get_root_tasks(self) -> tuple[TaskNode, ...]:
        """Get tasks with no dependencies (can start immediately).

        Tell, Don't Ask: Graph provides its own root tasks.

        Returns:
            Tuple of tasks that have no incoming dependencies
        """
        tasks_with_deps = {dep.to_task_id.value for dep in self.dependencies}
        return tuple(
            task for task in self.tasks
            if task.task_id.value not in tasks_with_deps
        )

    def get_execution_plan(self) -> ExecutionPlan:
        """Order tasks sequentially respecting dependencies (topological sort).

        Tell, Don't Ask: Graph knows how to order itself.

        Returns:
            ExecutionPlan describing the order in which tasks can execute.

        Raises:
            ValueError: If graph has circular dependencies
        """
        if self.has_circular_dependency():
            raise ValueError("Dependency graph contains circular dependencies")

        in_degree_map: dict[str, int] = {task.task_id.value: 0 for task in self.tasks}
        prerequisites_map: dict[str, set[str]] = {task.task_id.value: set() for task in self.tasks}

        for edge in self.dependencies:
            prerequisites_map[edge.from_task_id.value].add(edge.to_task_id.value)
            in_degree_map[edge.from_task_id.value] += 1

        nodes = tuple(
            TopologyNode(
                task=task,
                in_degree=in_degree_map[task.task_id.value],
                prerequisites=frozenset(prerequisites_map[task.task_id.value]),
            )
            for task in self.tasks
        )

        state = TopologyState(nodes)
        steps: list[ExecutionStep] = []

        while not state.is_empty():
            step, state = state.next_step(current_order=len(steps))
            steps.append(step)

        return ExecutionPlan(tuple(steps))

    def get_ordered_tasks(self) -> tuple[TaskNode, ...]:
        """Get tasks in topological order (flattened).

        Tell, Don't Ask: Graph knows how to order itself.
        Simpler alternative to get_execution_plan for consumers needing tuple.

        Returns:
            Tuple of tasks in dependency-respecting order
        """
        return self.get_execution_plan().tasks

    @classmethod
    def from_tasks(cls, tasks: tuple[TaskNode, ...]) -> DependencyGraph:
        """Factory method: Build dependency graph from tasks.

        Tell, Don't Ask: Graph knows how to build itself from tasks.
        Infers dependencies automatically using keyword heuristics.

        Args:
            tasks: Tasks to analyze

        Returns:
            DependencyGraph with inferred dependencies

        Raises:
            ValueError: If tasks is empty or graph is invalid
        """
        if not tasks:
            raise ValueError("tasks cannot be empty")

        # Infer dependencies using keyword matching heuristic
        dependencies = DependencyInferenceHelper.infer_dependencies_from_keywords(tasks)

        # Create graph (validation in __post_init__)
        return cls(tasks=tasks, dependencies=dependencies)

