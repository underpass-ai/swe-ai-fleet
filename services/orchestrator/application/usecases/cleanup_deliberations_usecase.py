"""Use case for cleaning up old deliberations."""

from __future__ import annotations

from typing import NamedTuple

from services.orchestrator.domain.entities import DeliberationStateRegistry


class CleanupResult(NamedTuple):
    """Result of cleanup operation.
    
    Attributes:
        timed_out_tasks: List of task IDs that timed out
        cleaned_up_tasks: List of task IDs that were cleaned up
        timed_out_count: Number of deliberations timed out
        cleaned_up_count: Number of deliberations cleaned up
    """
    
    timed_out_tasks: list[str]
    cleaned_up_tasks: list[str]
    timed_out_count: int
    cleaned_up_count: int


class CleanupDeliberationsUseCase:
    """Use case for timing out and cleaning up deliberations.
    
    This use case encapsulates the business logic for:
    - Detecting timed-out deliberations
    - Removing old completed/failed deliberations
    - Maintaining registry hygiene
    
    Following Clean Architecture:
    - Coordinates domain entities
    - No infrastructure dependencies
    - Returns typed results
    """
    
    def __init__(self, registry: DeliberationStateRegistry):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
        """
        self._registry = registry
    
    def execute(
        self,
        timeout_seconds: int,
        cleanup_after_seconds: int,
    ) -> CleanupResult:
        """Clean up timed-out and old deliberations.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
            cleanup_after_seconds: Cleanup threshold in seconds
            
        Returns:
            CleanupResult with lists of affected task IDs
            
        Example:
            >>> use_case = CleanupDeliberationsUseCase(registry)
            >>> result = use_case.execute(timeout_seconds=300, cleanup_after_seconds=3600)
            >>> print(f"Timed out: {result.timed_out_count}")
            >>> print(f"Cleaned up: {result.cleaned_up_count}")
        """
        # Get timed-out deliberations (Tell, Don't Ask)
        timed_out_states = self._registry.get_timed_out(timeout_seconds)
        timed_out_tasks = [state.task_id for state in timed_out_states]
        
        # Mark them as failed
        for state in timed_out_states:
            state.mark_failed(f"Timeout after {timeout_seconds}s")
        
        # Get deliberations ready for cleanup (Tell, Don't Ask)
        cleanup_states = self._registry.get_for_cleanup(cleanup_after_seconds)
        cleaned_up_tasks = [state.task_id for state in cleanup_states]
        
        # Remove from registry
        for state in cleanup_states:
            self._registry.remove_state(state.task_id)
        
        return CleanupResult(
            timed_out_tasks=timed_out_tasks,
            cleaned_up_tasks=cleaned_up_tasks,
            timed_out_count=len(timed_out_tasks),
            cleaned_up_count=len(cleaned_up_tasks),
        )

