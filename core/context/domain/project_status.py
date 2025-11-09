"""ProjectStatus enum - Status states for projects."""

from enum import Enum


class ProjectStatus(str, Enum):
    """Status states for Projects in the system.

    Projects represent the top-level work container (Product Owner's view).
    They have a simple lifecycle for tracking overall progress.

    Hierarchy: Project → Epic → Story → Task
    """

    # Active states
    ACTIVE = "active"  # Project is currently active
    PLANNING = "planning"  # Project is being planned
    IN_PROGRESS = "in_progress"  # Project has active work
    ON_HOLD = "on_hold"  # Project temporarily paused

    # Terminal states
    COMPLETED = "completed"  # Project successfully completed
    ARCHIVED = "archived"  # Project archived for historical reference
    CANCELLED = "cancelled"  # Project cancelled

    def __str__(self) -> str:
        """Return the string value.

        Returns:
            String value of the status
        """
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further work expected).

        Returns:
            True if terminal state
        """
        return self in {
            ProjectStatus.COMPLETED,
            ProjectStatus.ARCHIVED,
            ProjectStatus.CANCELLED,
        }

    def is_active_work(self) -> bool:
        """Check if project has active work ongoing.

        Returns:
            True if project is actively being worked on
        """
        return self in {
            ProjectStatus.ACTIVE,
            ProjectStatus.PLANNING,
            ProjectStatus.IN_PROGRESS,
        }

