"""DependencyGraph value object with business logic.

Value Object (DDD):
- Defined by its values, not identity
- Immutable (frozen=True)
- Contains domain logic (Tell, Don't Ask)
"""

from dataclasses import dataclass

from .dependency_edge import DependencyEdge
from .task_node import TaskNode


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
    
    def get_execution_levels(self) -> tuple[tuple[TaskNode, ...], ...]:
        """Order tasks by dependency levels (topological sort).
        
        Returns tasks grouped by execution level:
        - Level 0: Tasks with no dependencies (can start immediately)
        - Level 1: Tasks depending only on level 0
        - Level N: Tasks depending on level N-1 or earlier
        
        Tell, Don't Ask: Graph knows how to order itself.
        
        Returns:
            Tuple of tuples - each inner tuple is a level of tasks
            
        Raises:
            ValueError: If graph has circular dependencies
        """
        if self.has_circular_dependency():
            raise ValueError("Dependency graph contains circular dependencies")
        
        # Build adjacency list and in-degree count (using VO values)
        in_degree: dict[str, int] = {task.task_id.value: 0 for task in self.tasks}
        adjacency: dict[str, list[str]] = {task.task_id.value: [] for task in self.tasks}
        
        for dep in self.dependencies:
            adjacency[dep.to_task_id.value].append(dep.from_task_id.value)
            in_degree[dep.from_task_id.value] += 1
        
        # Topological sort by levels
        levels: list[tuple[TaskNode, ...]] = []
        remaining_tasks = {task.task_id.value: task for task in self.tasks}
        
        while remaining_tasks:
            # Find all tasks with no remaining dependencies
            current_level = tuple(
                task for task_id_val, task in remaining_tasks.items()
                if in_degree[task_id_val] == 0
            )
            
            if not current_level:
                # Should not happen if graph is acyclic (already validated)
                raise ValueError("Internal error: topological sort failed")
            
            levels.append(current_level)
            
            # Remove current level tasks and update in-degrees
            for task in current_level:
                del remaining_tasks[task.task_id.value]
                for dependent in adjacency[task.task_id.value]:
                    in_degree[dependent] -= 1
        
        return tuple(levels)

