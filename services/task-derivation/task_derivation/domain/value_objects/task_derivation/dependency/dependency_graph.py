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
        # Build adjacency list (using VO values for comparison)
        graph: dict[str, list[str]] = {task.task_id.value: [] for task in self.tasks}
        for dep in self.dependencies:
            graph[dep.from_task_id.value].append(dep.to_task_id.value)

        # DFS cycle detection
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task in self.tasks:
            if task.task_id.value not in visited:
                if has_cycle(task.task_id.value):
                    return True

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
        dependencies = cls._infer_dependencies_from_keywords(tasks)

        # Create graph (validation in __post_init__)
        return cls(tasks=tasks, dependencies=dependencies)

    @staticmethod
    def _infer_dependencies_from_keywords(
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
                # Tell, Don't Ask: Keyword knows how to match
                # Check if task_b mentions task_a's keywords
                for keyword in task_a.keywords:
                    if keyword.matches_in(str(task_b.title)):
                        dependencies.append(
                            DependencyEdge(
                                from_task_id=task_b.task_id,
                                to_task_id=task_a.task_id,
                                reason=DependencyReason(
                                    f"Task references '{keyword}' from prerequisite"
                                ),
                            )
                        )
                        break

                # Check if task_a mentions task_b's keywords
                for keyword in task_b.keywords:
                    if keyword.matches_in(str(task_a.title)):
                        dependencies.append(
                            DependencyEdge(
                                from_task_id=task_a.task_id,
                                to_task_id=task_b.task_id,
                                reason=DependencyReason(
                                    f"Task references '{keyword}' from prerequisite"
                                ),
                            )
                        )
                        break

        return tuple(dependencies)

