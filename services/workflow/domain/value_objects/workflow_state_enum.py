"""Workflow state enumeration.

Defines the 12 states of task execution workflow.
Following Domain-Driven Design principles.
"""

from enum import Enum


class WorkflowStateEnum(str, Enum):
    """Task workflow states.

    Represents the lifecycle of a task through multi-role validation.
    Flow: Developer → Architect → QA → PO

    Granularity: TASK level (not step level).
    Steps within a task are NOT persisted.
    """

    # Initial state
    TODO = "todo"

    # Developer states
    IMPLEMENTING = "implementing"
    DEV_COMPLETED = "dev_completed"  # Intermediate (auto-transitions)

    # Architect review states
    PENDING_ARCH_REVIEW = "pending_arch_review"
    ARCH_REVIEWING = "arch_reviewing"
    ARCH_APPROVED = "arch_approved"  # Intermediate (auto-transitions)
    ARCH_REJECTED = "arch_rejected"

    # QA testing states
    PENDING_QA = "pending_qa"
    QA_TESTING = "qa_testing"
    QA_PASSED = "qa_passed"  # Intermediate (auto-transitions)
    QA_FAILED = "qa_failed"

    # PO approval states
    PENDING_PO_APPROVAL = "pending_po_approval"
    PO_APPROVED = "po_approved"  # Intermediate (auto-transitions)

    # Terminal states
    DONE = "done"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (workflow finished)."""
        return self in (WorkflowStateEnum.DONE, WorkflowStateEnum.CANCELLED)

    def is_intermediate(self) -> bool:
        """Check if this is an intermediate state (auto-transitions)."""
        return self in (
            WorkflowStateEnum.DEV_COMPLETED,
            WorkflowStateEnum.ARCH_APPROVED,
            WorkflowStateEnum.QA_PASSED,
            WorkflowStateEnum.PO_APPROVED,
        )

    def is_waiting_for_role(self) -> bool:
        """Check if this state is waiting for a role to act."""
        return self in (
            WorkflowStateEnum.PENDING_ARCH_REVIEW,
            WorkflowStateEnum.PENDING_QA,
            WorkflowStateEnum.PENDING_PO_APPROVAL,
        )

    def get_responsible_role(self) -> str | None:
        """Get the role responsible for acting in this state."""
        role_mapping = {
            WorkflowStateEnum.TODO: None,  # System assigns
            WorkflowStateEnum.IMPLEMENTING: "developer",
            WorkflowStateEnum.DEV_COMPLETED: None,  # Auto-transition
            WorkflowStateEnum.PENDING_ARCH_REVIEW: "architect",
            WorkflowStateEnum.ARCH_REVIEWING: "architect",
            WorkflowStateEnum.ARCH_APPROVED: None,  # Auto-transition
            WorkflowStateEnum.ARCH_REJECTED: "developer",
            WorkflowStateEnum.PENDING_QA: "qa",
            WorkflowStateEnum.QA_TESTING: "qa",
            WorkflowStateEnum.QA_PASSED: None,  # Auto-transition
            WorkflowStateEnum.QA_FAILED: "developer",
            WorkflowStateEnum.PENDING_PO_APPROVAL: "po",
            WorkflowStateEnum.PO_APPROVED: None,  # Auto-transition
            WorkflowStateEnum.DONE: None,  # Terminal
            WorkflowStateEnum.CANCELLED: None,  # Terminal
        }
        return role_mapping.get(self)

