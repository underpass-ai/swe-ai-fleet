"""Domain value object for task status."""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class TaskStatus(Enum):
    """Domain value object representing the status of a task.
    
    This enum encapsulates all possible task statuses and provides
    business logic methods for status transitions and queries.
    """
    
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    
    @property
    def is_executable(self) -> bool:
        """Check if a task with this status can be executed.
        
        Returns:
            True if the task can be picked up for execution
        """
        return self in (TaskStatus.READY, TaskStatus.IN_PROGRESS)
    
    @property
    def is_final(self) -> bool:
        """Check if this status represents a final state.
        
        Returns:
            True if the task has reached a terminal state
        """
        return self in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED)
    
    @property
    def is_success(self) -> bool:
        """Check if this status represents successful completion.
        
        Returns:
            True if the task completed successfully
        """
        return self == TaskStatus.DONE
    
    @property
    def is_failure(self) -> bool:
        """Check if this status represents a failure.
        
        Returns:
            True if the task failed to complete
        """
        return self == TaskStatus.FAILED
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if a transition to the new status is valid.
        
        Args:
            new_status: The target status for the transition
            
        Returns:
            True if the transition is allowed by business rules
        """
        valid_transitions = {
            TaskStatus.READY: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
            TaskStatus.IN_PROGRESS: [TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.DONE: [],  # Terminal state
            TaskStatus.FAILED: [TaskStatus.READY],  # Can retry
            TaskStatus.CANCELLED: [],  # Terminal state
        }
        return new_status in valid_transitions.get(self, [])
    
    def __str__(self) -> str:
        """Return the string representation of the status."""
        return self.value
    
    @classmethod
    def from_string(cls, status_str: str) -> TaskStatus:
        """Create a TaskStatus from a string value.
        
        Args:
            status_str: String representation of the status
            
        Returns:
            TaskStatus enum value
            
        Raises:
            ValueError: If the string is not a valid status
        """
        try:
            return cls(status_str.upper())
        except ValueError as e:
            raise ValueError(f"Invalid task status: {status_str}") from e


class TaskWithStatus(Protocol):
    """Protocol for objects that have a task status."""
    status: str | TaskStatus
