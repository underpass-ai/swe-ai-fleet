"""Use case for executing deliberation on a council."""

from __future__ import annotations

import time
from typing import Any, NamedTuple

from services.orchestrator.domain.entities import OrchestratorStatistics


class DeliberationResult(NamedTuple):
    """Result of deliberation execution.
    
    Attributes:
        results: List of deliberation results from agents
        duration_ms: Duration of deliberation in milliseconds
        stats: Updated statistics entity
    """
    results: list[Any]
    duration_ms: int
    stats: OrchestratorStatistics


class DeliberateUseCase:
    """Use case for executing deliberation with a council of agents.
    
    This use case encapsulates the business logic for deliberation,
    delegating to the council to execute the actual deliberation process
    and updating statistics.
    
    Follows Single Responsibility Principle: orchestrates deliberation
    without knowing infrastructure details.
    """
    
    def __init__(self, stats: OrchestratorStatistics):
        """Initialize the use case.
        
        Args:
            stats: OrchestratorStatistics entity to update
        """
        self._stats = stats
    
    def execute(
        self,
        council: Any,
        role: str,
        task_description: str,
        constraints: Any
    ) -> DeliberationResult:
        """Execute deliberation with the given council.
        
        Args:
            council: Council instance that will execute deliberation
            role: Role of the council executing deliberation
            task_description: Description of the task to deliberate on
            constraints: Task constraints to apply
            
        Returns:
            DeliberationResult with results, duration, and updated stats
            
        Raises:
            RuntimeError: If council is None
            ValueError: If task description or role is empty
            
        Example:
            >>> stats = OrchestratorStatistics()
            >>> use_case = DeliberateUseCase(stats)
            >>> result = use_case.execute(council, "Coder", "Fix bug", constraints)
            >>> print(f"Duration: {result.duration_ms}ms")
        """
        # Fail-fast: Council must be provided
        if council is None:
            raise RuntimeError("Council cannot be None for deliberation execution")
        
        # Fail-fast: Role must be provided
        if not role or not role.strip():
            raise ValueError("Role cannot be empty for deliberation")
        
        # Fail-fast: Task description must be provided
        if not task_description or not task_description.strip():
            raise ValueError("Task description cannot be empty")
        
        # Measure execution time
        start_time = time.time()
        
        # Execute deliberation via council
        # The council handles the actual deliberation logic
        results = council.execute(task_description, constraints)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update statistics
        self._stats.increment_deliberation(role, duration_ms)
        
        # Return complete result with stats
        return DeliberationResult(
            results=results,
            duration_ms=duration_ms,
            stats=self._stats
        )

