"""Domain service for task selection logic."""

from __future__ import annotations

from typing import Protocol

from ..task_status import TaskStatus


class Task(Protocol):
    """Protocol for task objects used in selection."""
    id: str
    title: str
    status: str


class TaskSelectionService:
    """Domain service for selecting tasks based on business rules.
    
    This service encapsulates the logic for choosing which task to execute
    from a list of candidate tasks.
    """
    
    @staticmethod
    def pick_by_priority(tasks: list[Task]) -> Task:
        """Select a task based on priority criteria.
        
        Args:
            tasks: List of candidate tasks
            
        Returns:
            The highest priority task
            
        Note:
            Currently implements simple first-task selection.
            Can be extended with more sophisticated priority logic.
        """
        # Extend with domain's priority criteria if available
        return tasks[0]
    
    @staticmethod
    def filter_ready_tasks(tasks: list[Task]) -> list[Task]:
        """Filter tasks that are ready for execution.
        
        Args:
            tasks: List of all tasks
            
        Returns:
            List of tasks with status READY or IN_PROGRESS
        """
        ready_statuses = {TaskStatus.READY, TaskStatus.IN_PROGRESS}
        return [t for t in tasks if TaskStatus.from_string(str(t.status)) in ready_statuses]
    
    @staticmethod
    def select_task(tasks: list[Task], pick_first: bool = True) -> Task | None:
        """Select a task from the list based on the selection strategy.
        
        Args:
            tasks: List of candidate tasks
            pick_first: If True, pick the first ready task; otherwise use priority
            
        Returns:
            Selected task or None if no candidates
        """
        candidates = TaskSelectionService.filter_ready_tasks(tasks)
        if not candidates:
            return None
            
        return candidates[0] if pick_first else TaskSelectionService.pick_by_priority(candidates)
