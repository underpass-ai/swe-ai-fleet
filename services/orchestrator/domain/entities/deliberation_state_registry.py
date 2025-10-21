"""Deliberation state registry entity.

This entity manages a collection of deliberation states, providing
type-safe operations for tracking multiple deliberations.

Following Domain-Driven Design:
- Replaces dict[str, dict[str, Any]] with strong typing
- Encapsulates collection operations
- Applies "Tell, Don't Ask" principle
"""

from __future__ import annotations

from .deliberation_state import DeliberationState


class DeliberationStateRegistry:
    """Registry managing deliberation states.
    
    This entity encapsulates the collection of active deliberations,
    providing type-safe operations and business logic.
    
    Following "Tell, Don't Ask":
    - Tell registry to add/update states
    - Ask registry for states by task_id
    - Registry manages its own collection
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._states: dict[str, DeliberationState] = {}
    
    def start_tracking(
        self,
        task_id: str,
        expected_agents: int | None = None,
    ) -> DeliberationState:
        """Start tracking a new deliberation.
        
        Tell, Don't Ask: Tell registry to start tracking.
        
        Args:
            task_id: Task identifier
            expected_agents: Expected number of agents (optional)
            
        Returns:
            Created DeliberationState
            
        Raises:
            ValueError: If task_id already exists
        """
        if task_id in self._states:
            raise ValueError(f"Deliberation {task_id} already being tracked")
        
        state = DeliberationState(
            task_id=task_id,
            expected_agents=expected_agents,
        )
        self._states[task_id] = state
        return state
    
    def get_state(self, task_id: str) -> DeliberationState | None:
        """Get deliberation state by task_id.
        
        Args:
            task_id: Task identifier
            
        Returns:
            DeliberationState or None if not found
        """
        return self._states.get(task_id)
    
    def get_or_create(self, task_id: str) -> DeliberationState:
        """Get existing state or create new one if not found.
        
        Tell, Don't Ask: Tell registry to ensure state exists.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Existing or newly created DeliberationState
        """
        if task_id not in self._states:
            self._states[task_id] = DeliberationState(task_id=task_id)
        return self._states[task_id]
    
    def remove_state(self, task_id: str) -> DeliberationState | None:
        """Remove and return deliberation state.
        
        Tell, Don't Ask: Tell registry to remove state.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Removed DeliberationState or None if not found
        """
        return self._states.pop(task_id, None)
    
    def get_in_progress(self) -> list[DeliberationState]:
        """Get all deliberations in progress.
        
        Returns:
            List of DeliberationState entities with status "in_progress"
        """
        return [
            state for state in self._states.values()
            if state.is_in_progress()
        ]
    
    def get_timed_out(self, timeout_seconds: int) -> list[DeliberationState]:
        """Get all deliberations that have timed out.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
            
        Returns:
            List of DeliberationState entities that are timed out
        """
        return [
            state for state in self._states.values()
            if state.is_timed_out(timeout_seconds)
        ]
    
    def get_for_cleanup(self, cleanup_after_seconds: int) -> list[DeliberationState]:
        """Get all deliberations that should be cleaned up.
        
        Args:
            cleanup_after_seconds: Cleanup threshold in seconds
            
        Returns:
            List of DeliberationState entities ready for cleanup
        """
        return [
            state for state in self._states.values()
            if state.should_cleanup(cleanup_after_seconds)
        ]
    
    def count(self) -> int:
        """Get total number of tracked deliberations.
        
        Returns:
            Count of deliberations in registry
        """
        return len(self._states)
    
    def count_by_status(self) -> dict[str, int]:
        """Get counts grouped by status.
        
        Returns:
            Dictionary with counts per status
        """
        counts = {
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
        }
        
        for state in self._states.values():
            status = state.status
            if status in counts:
                counts[status] += 1
        
        return counts
    
    def to_stats_dict(self) -> dict[str, int]:
        """Create statistics dictionary.
        
        Tell, Don't Ask: Registry knows how to serialize its stats.
        
        Returns:
            Dictionary with deliberation statistics
        """
        counts = self.count_by_status()
        
        return {
            "total_deliberations": self.count(),
            "in_progress": counts["in_progress"],
            "completed": counts["completed"],
            "failed": counts["failed"],
        }

