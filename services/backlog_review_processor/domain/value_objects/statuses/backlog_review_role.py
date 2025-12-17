"""BacklogReviewRole enumeration."""

from enum import Enum


class BacklogReviewRole(str, Enum):
    """Enumeration of roles for backlog review councils.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe role names
    - NO magic strings
    """

    ARCHITECT = "ARCHITECT"
    QA = "QA"
    DEVOPS = "DEVOPS"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Role value
        """
        return self.value
