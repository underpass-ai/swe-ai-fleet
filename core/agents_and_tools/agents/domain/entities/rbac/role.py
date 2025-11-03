"""Domain value object for Role in RBAC system."""

from dataclasses import dataclass
from enum import Enum

from .action import Action, ActionEnum, ScopeEnum


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

    A Role defines what actions an agent can perform and the scope of those actions.
    This enables RBAC (Role-Based Access Control) at the domain level.

    Domain Invariants:
    - Role must be a valid RoleEnum value
    - Allowed actions are defined by role
    - Scope matches role's domain
    - Roles are immutable

    Examples:
        >>> role = Role(
        ...     value=RoleEnum.ARCHITECT,
        ...     allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
        ...     scope=ScopeEnum.TECHNICAL,
        ... )
        >>> role.get_name()
        'architect'
    """

    value: RoleEnum
    allowed_actions: frozenset[ActionEnum]
    scope: ScopeEnum

    def __post_init__(self) -> None:
        """Validate role values (fail-fast).

        Raises:
            ValueError: If role is not a valid RoleEnum
            ValueError: If allowed_actions is empty
            ValueError: If scope is not a valid ScopeEnum
        """
        if not isinstance(self.value, RoleEnum):
            raise ValueError(f"Invalid role: {self.value}. Must be RoleEnum.")
        if not self.allowed_actions:
            raise ValueError("allowed_actions cannot be empty")
        if not isinstance(self.scope, ScopeEnum):
            raise ValueError(f"Invalid scope: {self.scope}. Must be ScopeEnum.")

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
        """Get role name as string.

        Returns:
            Role name (e.g., "architect", "qa")
        """
        return self.value.value

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

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value

