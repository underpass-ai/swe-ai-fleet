"""ProjectStatus enum for Planning Service."""

from enum import Enum


class ProjectStatus(str, Enum):
    """Status states for Projects.

    Projects have a simple lifecycle for tracking overall progress.
    """

    # Active states
    ACTIVE = "active"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"

    # Terminal states
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return string value.

        Returns:
            String representation
        """
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state.

        Returns:
            True if terminal
        """
        return self in {
            ProjectStatus.COMPLETED,
            ProjectStatus.ARCHIVED,
            ProjectStatus.CANCELLED,
        }

    def is_active_work(self) -> bool:
        """Check if project has active work.

        Returns:
            True if active work ongoing
        """
        return self in {
            ProjectStatus.ACTIVE,
            ProjectStatus.PLANNING,
            ProjectStatus.IN_PROGRESS,
        }

