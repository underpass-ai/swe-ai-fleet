"""ACTION_SCOPES: Mapping of actions to their scopes."""

from core.shared.domain.action_enum import ActionEnum
from core.shared.domain.scope_enum import ScopeEnum

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
    ActionEnum.CLAIM_TESTING: ScopeEnum.WORKFLOW,
    ActionEnum.REQUEST_REVIEW: ScopeEnum.WORKFLOW,
    ActionEnum.RETRY: ScopeEnum.WORKFLOW,
    ActionEnum.CANCEL: ScopeEnum.WORKFLOW,
    ActionEnum.DISCARD_TASK: ScopeEnum.WORKFLOW,
    ActionEnum.ASSIGN_TO_DEVELOPER: ScopeEnum.WORKFLOW,
    ActionEnum.AUTO_ROUTE_TO_ARCHITECT: ScopeEnum.WORKFLOW,
    ActionEnum.AUTO_ROUTE_TO_QA: ScopeEnum.WORKFLOW,
    ActionEnum.AUTO_ROUTE_TO_PO: ScopeEnum.WORKFLOW,
    ActionEnum.AUTO_COMPLETE: ScopeEnum.WORKFLOW,
    ActionEnum.NO_ACTION: ScopeEnum.WORKFLOW,
}

