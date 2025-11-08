"""Domain value object for Role in RBAC system."""

from dataclasses import dataclass
from enum import Enum

from core.shared.domain import Action, ActionEnum, ScopeEnum


class RoleEnum(str, Enum):
    """
    Enumeration of agent roles in the SWE team.

    Roles:
    - ARCHITECT: Technical leadership, architectural decisions
    - QA: Quality assurance, testing, spec validation
    - DEVELOPER: Feature implementation, bug fixes
    - PO: Product owner, business decisions
    - DEVOPS: Deployment, infrastructure operations
    - DATA: Database, data management
    """

    ARCHITECT = "architect"
    QA = "qa"
    DEVELOPER = "developer"
    PO = "po"
    DEVOPS = "devops"
    DATA = "data"


@dataclass(frozen=True)
class Role:
    """Value Object: Agent's role in the SWE team.

    A Role defines what actions an agent can perform, what tools it can use,
    and the scope of those operations. This enables RBAC (Role-Based Access Control)
    at the domain level.

    Domain Invariants:
    - Role must be a valid RoleEnum value
    - Allowed actions are defined by role
    - Allowed tools are defined by role
    - Scope matches role's domain
    - Roles are immutable

    Examples:
        >>> role = Role(
        ...     value=RoleEnum.ARCHITECT,
        ...     allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
        ...     allowed_tools=frozenset(["files", "git", "db"]),
        ...     scope=ScopeEnum.TECHNICAL,
        ... )
        >>> role.get_name()
        'architect'
        >>> "git" in role.allowed_tools
        True
    """

    value: RoleEnum
    allowed_actions: frozenset[ActionEnum]
    allowed_tools: frozenset[str]
    scope: ScopeEnum

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        This validates business rules only.

        Raises:
            ValueError: If allowed_actions is empty
            ValueError: If allowed_tools is empty
        """
        if not self.allowed_actions:
            raise ValueError("allowed_actions cannot be empty")
        if not self.allowed_tools:
            raise ValueError("allowed_tools cannot be empty")

    def can_perform(self, action: Action) -> bool:
        """Check if this role can perform the given action.

        Business Rules:
        1. Action MUST be in allowed_actions
        2. Action scope MUST match role scope

        Scope compatibility enforces boundaries:
        - Architect (technical) can approve technical decisions
        - QA (quality) can validate spec, NOT approve technical designs
        - PO (business) can approve business proposals
        - Cross-scope actions are forbidden

        Args:
            action: The action to check

        Returns:
            True if role can perform action, False otherwise

        Examples:
            >>> architect = Role(
            ...     value=RoleEnum.ARCHITECT,
            ...     allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            ...     scope=ScopeEnum.TECHNICAL,
            ... )
            >>> approve_design = Action(value=ActionEnum.APPROVE_DESIGN)
            >>> architect.can_perform(approve_design)
            True
        """
        return (
            action.value in self.allowed_actions
            and action.get_scope() == self.scope
        )

    def get_name(self) -> str:
        """Get role name as string (lowercase).

        Returns:
            Role name (e.g., "architect", "qa")
        """
        return self.value.value

    def get_prompt_key(self) -> str:
        """Get role name for prompt template lookup (uppercase).

        Tell, Don't Ask: Role knows how to format itself for prompt lookups.

        Returns:
            Role name in uppercase (e.g., "ARCHITECT", "QA")
        """
        return self.value.value.upper()

    def is_architect(self) -> bool:
        """Check if role is Architect."""
        return self.value == RoleEnum.ARCHITECT

    def is_qa(self) -> bool:
        """Check if role is QA."""
        return self.value == RoleEnum.QA

    def is_developer(self) -> bool:
        """Check if role is Developer."""
        return self.value == RoleEnum.DEVELOPER

    def is_po(self) -> bool:
        """Check if role is Product Owner."""
        return self.value == RoleEnum.PO

    def is_devops(self) -> bool:
        """Check if role is DevOps."""
        return self.value == RoleEnum.DEVOPS

    def is_data(self) -> bool:
        """Check if role is Data."""
        return self.value == RoleEnum.DATA

    def has_tool_access(self, tool_name: str) -> bool:
        """Check if role has access to a specific tool.

        Tell, Don't Ask: Role knows which tools it can access.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is allowed, False otherwise

        Examples:
            >>> developer = RoleFactory.create_developer()
            >>> developer.has_tool_access("git")
            True
            >>> developer.has_tool_access("db")
            False
        """
        return tool_name in self.allowed_tools

    def get_allowed_tools_list(self) -> list[str]:
        """Get list of allowed tools.

        Tell, Don't Ask: Role provides its tools as a list.

        Returns:
            Sorted list of allowed tool names
        """
        return sorted(self.allowed_tools)

    def get_allowed_actions_list(self) -> list[str]:
        """Get list of allowed actions as strings.

        Tell, Don't Ask: Role provides its actions as strings.

        Returns:
            Sorted list of allowed action names
        """
        return sorted([action.value for action in self.allowed_actions])

    def is_technical_role(self) -> bool:
        """Check if this is a technical role (architect, developer)."""
        return self.scope == ScopeEnum.TECHNICAL

    def is_business_role(self) -> bool:
        """Check if this is a business role (PO)."""
        return self.scope == ScopeEnum.BUSINESS

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value

