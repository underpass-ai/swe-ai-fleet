"""Action: Domain value object for Action in RBAC system."""

from dataclasses import dataclass

from core.shared.domain.action_enum import ActionEnum
from core.shared.domain.action_scopes import ACTION_SCOPES
from core.shared.domain.scope_enum import ScopeEnum


@dataclass(frozen=True)
class Action:
    """Value Object: Action that an agent can execute.

    Wraps ActionEnum and provides scope information for RBAC enforcement.

    Domain Invariants:
    - Action must be a valid ActionEnum value
    - Scope is determined by ACTION_SCOPES mapping
    - Actions are immutable

    Examples:
        >>> action = Action(value=ActionEnum.APPROVE_DESIGN)
        >>> action.get_scope()
        <ScopeEnum.TECHNICAL: 'technical'>
        >>> action.is_technical()
        True
    """

    value: ActionEnum

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        No additional business rules to validate.
        """
        pass  # No validation needed, type hint ensures ActionEnum

    @staticmethod
    def from_action_enum(action_enum: ActionEnum) -> "Action":
        """Factory method: Create Action from ActionEnum.

        Args:
            action_enum: ActionEnum value

        Returns:
            Action value object wrapping the enum
        """
        return Action(value=action_enum)

    def get_scope(self) -> ScopeEnum:
        """Get the scope of this action.

        Returns:
            ScopeEnum representing the action's scope
        """
        return ACTION_SCOPES[self.value]

    def is_technical(self) -> bool:
        """Check if action is in technical scope."""
        return self.get_scope() == ScopeEnum.TECHNICAL

    def is_business(self) -> bool:
        """Check if action is in business scope."""
        return self.get_scope() == ScopeEnum.BUSINESS

    def is_quality(self) -> bool:
        """Check if action is in quality scope."""
        return self.get_scope() == ScopeEnum.QUALITY

    def is_operations(self) -> bool:
        """Check if action is in operations scope."""
        return self.get_scope() == ScopeEnum.OPERATIONS

    def is_data(self) -> bool:
        """Check if action is in data scope."""
        return self.get_scope() == ScopeEnum.DATA

    def is_workflow(self) -> bool:
        """Check if action is in workflow scope."""
        return self.get_scope() == ScopeEnum.WORKFLOW

    def is_rejection(self) -> bool:
        """Check if this action represents a rejection.

        Domain knowledge: Which actions are rejections.
        """
        return self.value in (
            ActionEnum.REJECT_DESIGN,
            ActionEnum.REJECT_TESTS,
            ActionEnum.REJECT_STORY,
            ActionEnum.REJECT_PROPOSAL,
        )

    def is_approval(self) -> bool:
        """Check if this action represents an approval.

        Domain knowledge: Which actions are approvals.
        """
        return self.value in (
            ActionEnum.APPROVE_DESIGN,
            ActionEnum.APPROVE_TESTS,
            ActionEnum.APPROVE_STORY,
            ActionEnum.APPROVE_PROPOSAL,
            ActionEnum.APPROVE_SCOPE,
        )

    def get_value(self) -> str:
        """Get action value as string.

        Tell, Don't Ask: Encapsulate attribute access.
        Instead of: action.value.value
        Use: action.get_value()

        Returns:
            Action string (e.g., "approve_design", "commit_code")
        """
        return self.value.value

    def to_string(self) -> str:
        """Convert action to string representation.

        Deprecated: Use get_value() instead for consistency.

        Returns:
            String representation (e.g., "approve_design")
        """
        return self.get_value()

    def __str__(self) -> str:
        """String representation for logging."""
        return self.get_value()
