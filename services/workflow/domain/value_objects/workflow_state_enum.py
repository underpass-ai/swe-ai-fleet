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
        """Check if this state is waiting for a role to start work.

        Returns True only for PENDING states where tasks are waiting
        for assignment to a specific agent of that role.

        Does NOT include active states (IMPLEMENTING, ARCH_REVIEWING, QA_TESTING)
        to avoid race conditions in multi-agent teams where multiple agents
        of the same role could claim already-assigned tasks.

        Future: When agent_id tracking is added to WorkflowState, active states
        can be included with agent-specific filtering.
        """
        return self in (
            WorkflowStateEnum.PENDING_ARCH_REVIEW,
            WorkflowStateEnum.PENDING_QA,
            WorkflowStateEnum.PENDING_PO_APPROVAL,
        )

