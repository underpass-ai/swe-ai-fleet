"""Role enum - User/Agent roles in the system."""

from enum import Enum


class Role(str, Enum):
    """Roles in the SWE AI Fleet system.

    Each role has different responsibilities and data access patterns:
    - PO: Product Owner (human, full access)
    - ARCHITECT: System design, technical decisions
    - DEVELOPER: Code implementation
    - QA: Testing, quality assurance
    - REVIEWER: Code review
    - COACH: Story refinement, guidance
    - ORCHESTRATOR: Task coordination
    """

    # Human roles
    PRODUCT_OWNER = "product_owner"
    PO = "po"  # Alias

    # Agent roles
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA = "qa"
    TESTER = "tester"  # Alias
    REVIEWER = "reviewer"
    COACH = "coach"
    STORY_COACH = "story_coach"  # Alias
    ORCHESTRATOR = "orchestrator"

    # System roles
    SYSTEM = "system"
    ADMIN = "admin"

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    def is_human(self) -> bool:
        """Check if this is a human role.

        Returns:
            True if role is for human users
        """
        return self in {Role.PRODUCT_OWNER, Role.PO, Role.ADMIN}

    def is_agent(self) -> bool:
        """Check if this is an agent role.

        Returns:
            True if role is for AI agents
        """
        return self in {
            Role.ARCHITECT,
            Role.DEVELOPER,
            Role.QA,
            Role.TESTER,
            Role.REVIEWER,
            Role.COACH,
            Role.STORY_COACH,
            Role.ORCHESTRATOR,
        }

    def has_full_context_access(self) -> bool:
        """Check if role has access to full context (RBAC L3).

        Returns:
            True if role can see all data
        """
        # PO and ADMIN have full access
        return self in {Role.PRODUCT_OWNER, Role.PO, Role.ADMIN}

