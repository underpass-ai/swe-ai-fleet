"""BacklogReviewRole enum for Planning Service.

Defines review roles for backlog review ceremonies.
These are the specific roles that participate in backlog review.
"""

from enum import Enum


class BacklogReviewRole(str, Enum):
    """Review roles for backlog review ceremonies.

    These roles participate in the backlog review ceremony to provide
    specialized feedback before planning:
    - ARCHITECT: Technical architecture and design review
    - QA: Quality assurance and testability review
    - DEVOPS: Infrastructure and deployment review

    Aligned with orchestrator council roles for consistency.
    """

    ARCHITECT = "ARCHITECT"  # Technical architecture review
    QA = "QA"                # Quality assurance review
    DEVOPS = "DEVOPS"        # Infrastructure and operations review

    def __str__(self) -> str:
        """Return string value.

        Returns:
            String representation
        """
        return self.value

    @classmethod
    def all_roles(cls) -> tuple["BacklogReviewRole", ...]:
        """Get all review roles.

        Returns:
            Tuple of all review roles
        """
        return (cls.ARCHITECT, cls.QA, cls.DEVOPS)
