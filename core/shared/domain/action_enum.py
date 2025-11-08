"""ActionEnum: Enumeration of all actions in the RBAC system."""

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
    # Only actions that cause FSM state transitions
    CLAIM_TASK = "claim_task"
    CLAIM_REVIEW = "claim_review"
    CLAIM_TESTING = "claim_testing"
    REQUEST_REVIEW = "request_review"
    RETRY = "retry"
    CANCEL = "cancel"
    DISCARD_TASK = "discard_task"  # PO discards task

    # System routing actions (auto-transitions)
    ASSIGN_TO_DEVELOPER = "assign_to_developer"
    AUTO_ROUTE_TO_ARCHITECT = "auto_route_to_architect"
    AUTO_ROUTE_TO_QA = "auto_route_to_qa"
    AUTO_ROUTE_TO_PO = "auto_route_to_po"
    AUTO_COMPLETE = "auto_complete"

    # Special values (semantic nulls)
    NO_ACTION = "no_action"  # Used when no action is required (terminal/auto states)

