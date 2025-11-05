"""Domain value object for Action in RBAC system."""

from dataclasses import dataclass
from enum import Enum


class ActionEnum(str, Enum):
    """
    Enumeration of all actions that agents can perform in the system.

    Actions are categorized by scope:
    - TECHNICAL: Architecture, development, code review
    - BUSINESS: Product decisions, scope approval
    - QUALITY: Testing, compliance validation
    - OPERATIONS: Deployment, infrastructure
    - DATA: Database, migrations
    - WORKFLOW: Task lifecycle management
    """

    # Technical actions (Architect, Developer)
    APPROVE_DESIGN = "approve_design"
    REJECT_DESIGN = "reject_design"
    REVIEW_ARCHITECTURE = "review_architecture"
    EXECUTE_TASK = "execute_task"
    RUN_TESTS = "run_tests"
    COMMIT_CODE = "commit_code"
    REVISE_CODE = "revise_code"

    # Business actions (Product Owner)
    APPROVE_PROPOSAL = "approve_proposal"
    REJECT_PROPOSAL = "reject_proposal"
    REQUEST_REFINEMENT = "request_refinement"
    APPROVE_SCOPE = "approve_scope"
    MODIFY_CONSTRAINTS = "modify_constraints"
    APPROVE_STORY = "approve_story"
    REJECT_STORY = "reject_story"

    # Quality actions (QA)
    APPROVE_TESTS = "approve_tests"
    REJECT_TESTS = "reject_tests"
    VALIDATE_COMPLIANCE = "validate_compliance"
    VALIDATE_SPEC = "validate_spec"

    # Operations actions (DevOps)
    DEPLOY_SERVICE = "deploy_service"
    CONFIGURE_INFRA = "configure_infra"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"

    # Data actions (Data)
    EXECUTE_MIGRATION = "execute_migration"
    VALIDATE_SCHEMA = "validate_schema"

    # Workflow actions (System + Agents)
    CLAIM_TASK = "claim_task"
    CLAIM_REVIEW = "claim_review"
    REQUEST_REVIEW = "request_review"
    RETRY = "retry"
    CANCEL = "cancel"


class ScopeEnum(str, Enum):
    """
    Enumeration of action scopes.

    Scopes enforce role boundaries:
    - Architect operates in TECHNICAL scope
    - PO operates in BUSINESS scope
    - QA operates in QUALITY scope
    - DevOps operates in OPERATIONS scope
    - Data operates in DATA scope
    - WORKFLOW is cross-cutting (system operations)
    """

    TECHNICAL = "technical"
    BUSINESS = "business"
    QUALITY = "quality"
    OPERATIONS = "operations"
    DATA = "data"
    WORKFLOW = "workflow"


# Mapping of actions to their scopes
ACTION_SCOPES: dict[ActionEnum, ScopeEnum] = {
    # Technical scope
    ActionEnum.APPROVE_DESIGN: ScopeEnum.TECHNICAL,
    ActionEnum.REJECT_DESIGN: ScopeEnum.TECHNICAL,
    ActionEnum.REVIEW_ARCHITECTURE: ScopeEnum.TECHNICAL,
    ActionEnum.EXECUTE_TASK: ScopeEnum.TECHNICAL,
    ActionEnum.RUN_TESTS: ScopeEnum.TECHNICAL,
    ActionEnum.COMMIT_CODE: ScopeEnum.TECHNICAL,
    ActionEnum.REVISE_CODE: ScopeEnum.TECHNICAL,
    # Business scope
    ActionEnum.APPROVE_PROPOSAL: ScopeEnum.BUSINESS,
    ActionEnum.REJECT_PROPOSAL: ScopeEnum.BUSINESS,
    ActionEnum.REQUEST_REFINEMENT: ScopeEnum.BUSINESS,
    ActionEnum.APPROVE_SCOPE: ScopeEnum.BUSINESS,
    ActionEnum.MODIFY_CONSTRAINTS: ScopeEnum.BUSINESS,
    ActionEnum.APPROVE_STORY: ScopeEnum.BUSINESS,
    ActionEnum.REJECT_STORY: ScopeEnum.BUSINESS,
    # Quality scope
    ActionEnum.APPROVE_TESTS: ScopeEnum.QUALITY,
    ActionEnum.REJECT_TESTS: ScopeEnum.QUALITY,
    ActionEnum.VALIDATE_COMPLIANCE: ScopeEnum.QUALITY,
    ActionEnum.VALIDATE_SPEC: ScopeEnum.QUALITY,
    # Operations scope
    ActionEnum.DEPLOY_SERVICE: ScopeEnum.OPERATIONS,
    ActionEnum.CONFIGURE_INFRA: ScopeEnum.OPERATIONS,
    ActionEnum.ROLLBACK_DEPLOYMENT: ScopeEnum.OPERATIONS,
    # Data scope
    ActionEnum.EXECUTE_MIGRATION: ScopeEnum.DATA,
    ActionEnum.VALIDATE_SCHEMA: ScopeEnum.DATA,
    # Workflow scope (cross-cutting system operations)
    ActionEnum.CLAIM_TASK: ScopeEnum.WORKFLOW,
    ActionEnum.CLAIM_REVIEW: ScopeEnum.WORKFLOW,
    ActionEnum.REQUEST_REVIEW: ScopeEnum.WORKFLOW,
    ActionEnum.RETRY: ScopeEnum.WORKFLOW,
    ActionEnum.CANCEL: ScopeEnum.WORKFLOW,
}


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

    def to_string(self) -> str:
        """Convert action to string representation.

        Returns:
            String representation (e.g., "approve_design")
        """
        return self.value.value

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value

