"""Deliberation Tracker Port (interface).

This port was used for tracking deliberation state but is no longer actively used.
Kept for backward compatibility with tests.
"""

from typing import Protocol


class DeliberationNotFoundError(Exception):
    """Exception raised when a deliberation is not found."""

    def __init__(self, task_id: str) -> None:
        """Initialize error.

        Args:
            task_id: Task ID that was not found
        """
        self.task_id = task_id
        super().__init__(f"Deliberation not found for task: {task_id}")


class DeliberationTrackerPort(Protocol):
    """Port for tracking deliberation state.

    DEPRECATED: This port is no longer actively used.
    Kept for backward compatibility.
    """

    async def get_deliberation_id(self, task_id: str) -> str:
        """Get deliberation ID for a task.

        Args:
            task_id: Task identifier

        Returns:
            Deliberation ID

        Raises:
            DeliberationNotFoundError: If deliberation not found
        """
        ...





