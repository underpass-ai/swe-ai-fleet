"""Use case for getting deliberation results."""

from __future__ import annotations

from typing import Any, NamedTuple

from services.orchestrator.domain.entities import DeliberationStateRegistry


class DeliberationResultQueryResult(NamedTuple):
    """Result of deliberation result query.
    
    Attributes:
        task_id: Task identifier
        status: Current status (raw string)
        results: List of agent results
        error_message: Error message if failed
        duration_ms: Duration in milliseconds
        total_agents: Expected number of agents
        received_count: Number of responses received
        failed_count: Number of failed agents
    """
    
    task_id: str
    status: str
    results: list[dict[str, Any]]
    error_message: str
    duration_ms: int
    total_agents: int | None
    received_count: int
    failed_count: int


class GetDeliberationResultUseCase:
    """Use case for querying deliberation results.
    
    This use case encapsulates the business logic for retrieving
    the current state and results of a deliberation.
    
    Following Clean Architecture:
    - Use case coordinates domain entities
    - Returns domain-level result (status as string, not proto enum)
    - Infrastructure layer maps to proto enums
    """
    
    def __init__(self, registry: DeliberationStateRegistry):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
        """
        self._registry = registry
    
    def execute(self, task_id: str) -> DeliberationResultQueryResult | None:
        """Get deliberation result by task_id.
        
        Args:
            task_id: Task identifier to query
            
        Returns:
            DeliberationResultQueryResult or None if not found
            
        Example:
            >>> use_case = GetDeliberationResultUseCase(registry)
            >>> result = use_case.execute("task-001")
            >>> if result:
            ...     print(f"Status: {result.status}")
        """
        state = self._registry.get_state(task_id)
        if not state:
            return None
        
        # Get result dict from domain entity (Tell, Don't Ask)
        result_dict = state.to_query_result_dict()
        
        # Return as NamedTuple for type safety
        return DeliberationResultQueryResult(
            task_id=result_dict["task_id"],
            status=result_dict["status"],
            results=result_dict["results"],
            error_message=result_dict["error_message"],
            duration_ms=result_dict["duration_ms"],
            total_agents=result_dict["total_agents"],
            received_count=result_dict["received_count"],
            failed_count=result_dict["failed_count"],
        )

