"""Dependency inference utility for keyword-based dependency detection.

Utility class for inferring task dependencies based on keyword matching.
Following DDD: Pure domain logic, no infrastructure dependencies.
"""

from ..content.dependency_reason import DependencyReason
from .dependency_edge import DependencyEdge
from .task_node import TaskNode


class DependencyInference:
    """Utility class for inferring task dependencies from keywords.

    Pure domain logic utility - no state, only static methods.
    Following DDD: Domain service pattern for cross-cutting concerns.
    """

    @staticmethod
    def infer_dependencies_from_keywords(
        tasks: tuple[TaskNode, ...]
    ) -> tuple[DependencyEdge, ...]:
        """Infer dependencies based on keyword matching.

        Business logic for dependency inference.
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
                dep = DependencyInference.check_keyword_dependency(task_a, task_b)
                if dep:
                    dependencies.append(dep)

        return tuple(dependencies)

    @staticmethod
    def check_keyword_dependency(
        task_a: TaskNode, task_b: TaskNode
    ) -> DependencyEdge | None:
        """Check if two tasks have a keyword-based dependency.

        Checks bidirectional: A→B and B→A.

        Args:
            task_a: First task
            task_b: Second task

        Returns:
            DependencyEdge if dependency found, None otherwise
        """
        # Check if task_b mentions task_a's keywords
        dep = DependencyInference.find_keyword_match(task_a, task_b)
        if dep:
            return dep

        # Check if task_a mentions task_b's keywords
        matched_keyword = DependencyInference.find_matching_keyword(task_b, task_a)
        if matched_keyword:
            return DependencyEdge(
                from_task_id=task_a.task_id,
                to_task_id=task_b.task_id,
                reason=DependencyReason(
                    f"Task references '{matched_keyword}' from prerequisite"
                ),
            )

        return None

    @staticmethod
    def find_keyword_match(
        source_task: TaskNode, target_task: TaskNode
    ) -> DependencyEdge | None:
        """Find if source task's keywords match in target task's title.

        Args:
            source_task: Task with keywords to search
            target_task: Task with title to search in

        Returns:
            DependencyEdge if match found, None otherwise
        """
        matched_keyword = DependencyInference.find_matching_keyword(
            source_task, target_task
        )
        if matched_keyword:
            return DependencyEdge(
                from_task_id=target_task.task_id,
                to_task_id=source_task.task_id,
                reason=DependencyReason(
                    f"Task references '{matched_keyword}' from prerequisite"
                ),
            )
        return None

    @staticmethod
    def find_matching_keyword(
        source_task: TaskNode, target_task: TaskNode
    ) -> str | None:
        """Find first keyword from source_task that matches in target_task's title.

        Args:
            source_task: Task with keywords to search
            target_task: Task with title to search in

        Returns:
            Matched keyword string if found, None otherwise
        """
        for keyword in source_task.keywords:
            if keyword.matches_in(str(target_task.title)):
                return str(keyword)
        return None

    @staticmethod
    def has_cycle_dfs(
        node: str,
        graph: dict[str, list[str]],
        visited: set[str],
        rec_stack: set[str],
    ) -> bool:
        """Perform DFS to detect cycles in graph.

        Utility method for cycle detection in dependency graphs.
        Used by DependencyGraph for circular dependency validation.

        Args:
            node: Current node to check
            graph: Adjacency list representation
            visited: Set of visited nodes
            rec_stack: Set of nodes in current recursion path

        Returns:
            True if cycle detected from this node
        """
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph[node]:
            if neighbor in rec_stack:
                return True
            if neighbor not in visited:
                if DependencyInference.has_cycle_dfs(neighbor, graph, visited, rec_stack):
                    return True

        rec_stack.remove(node)
        return False

