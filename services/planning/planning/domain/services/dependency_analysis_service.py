"""Domain service for analyzing task dependencies.

Domain Service (DDD):
- Stateless service
- Pure business logic
- NO infrastructure concerns
- Coordinates operations on domain objects
- Uses ONLY Value Objects (NO primitives)
"""

from planning.domain.value_objects.dependency_edge import DependencyEdge
from planning.domain.value_objects.dependency_graph import DependencyGraph
from planning.domain.value_objects.dependency_reason import DependencyReason
from planning.domain.value_objects.task_node import TaskNode


class DependencyAnalysisService:
    """Domain service for analyzing task dependencies.
    
    Following DDD:
    - Stateless service (pure functions)
    - Business logic for dependency inference
    - NO infrastructure concerns (NO DB, NO LLM, NO HTTP)
    - Uses ONLY Value Objects (NO primitives)
    
    This service provides HEURISTICS for dependency analysis.
    It doesn't make external calls - that's the responsibility of use cases.
    """
    
    @staticmethod
    def infer_dependencies_from_keywords(
        tasks: tuple[TaskNode, ...]
    ) -> tuple[DependencyEdge, ...]:
        """Infer dependencies based on keyword matching.
        
        Simple heuristic: If task B mentions task A's keywords,
        then B likely depends on A.
        
        Tell, Don't Ask: Uses TaskNode.has_keyword_matching()
        
        Args:
            tasks: Tuple of task nodes to analyze
            
        Returns:
            Tuple of inferred dependency edges
            
        Raises:
            ValueError: If tasks is empty
        """
        if not tasks:
            raise ValueError("tasks cannot be empty")
        
        dependencies: list[DependencyEdge] = []
        
        for i, task_a in enumerate(tasks):
            for task_b in tasks[i + 1:]:
                # Tell, Don't Ask: TaskNode knows how to match keywords
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
    
    @staticmethod
    def build_dependency_graph(
        tasks: tuple[TaskNode, ...],
        dependencies: tuple[DependencyEdge, ...],
    ) -> DependencyGraph:
        """Build and validate dependency graph.
        
        Factory method that creates DependencyGraph with validation.
        
        Args:
            tasks: Task nodes
            dependencies: Dependency edges
            
        Returns:
            Validated dependency graph
            
        Raises:
            ValueError: If graph is invalid (circular deps, unknown tasks, etc.)
        """
        # DependencyGraph validates itself in __post_init__
        graph = DependencyGraph(tasks=tasks, dependencies=dependencies)
        
        # Additional validation: no circular dependencies
        if graph.has_circular_dependency():
            raise ValueError("Dependency graph contains circular dependencies")
        
        return graph

