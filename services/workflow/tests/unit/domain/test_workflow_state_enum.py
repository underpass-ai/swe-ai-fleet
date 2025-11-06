"""Unit tests for WorkflowStateEnum."""

from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def test_workflow_state_enum_values():
    """Test all workflow state enum values exist."""
    assert WorkflowStateEnum.TODO.value == "todo"
    assert WorkflowStateEnum.IMPLEMENTING.value == "implementing"
    assert WorkflowStateEnum.DEV_COMPLETED.value == "dev_completed"
    assert WorkflowStateEnum.PENDING_ARCH_REVIEW.value == "pending_arch_review"
    assert WorkflowStateEnum.ARCH_REVIEWING.value == "arch_reviewing"
    assert WorkflowStateEnum.ARCH_APPROVED.value == "arch_approved"
    assert WorkflowStateEnum.ARCH_REJECTED.value == "arch_rejected"
    assert WorkflowStateEnum.PENDING_QA.value == "pending_qa"
    assert WorkflowStateEnum.QA_TESTING.value == "qa_testing"
    assert WorkflowStateEnum.QA_PASSED.value == "qa_passed"
    assert WorkflowStateEnum.QA_FAILED.value == "qa_failed"
    assert WorkflowStateEnum.PENDING_PO_APPROVAL.value == "pending_po_approval"
    assert WorkflowStateEnum.PO_APPROVED.value == "po_approved"
    assert WorkflowStateEnum.DONE.value == "done"
    assert WorkflowStateEnum.CANCELLED.value == "cancelled"


def test_is_terminal():
    """Test is_terminal() method."""
    assert WorkflowStateEnum.DONE.is_terminal() is True
    assert WorkflowStateEnum.CANCELLED.is_terminal() is True
    assert WorkflowStateEnum.IMPLEMENTING.is_terminal() is False
    assert WorkflowStateEnum.PENDING_ARCH_REVIEW.is_terminal() is False


def test_is_intermediate():
    """Test is_intermediate() method (auto-transition states)."""
    assert WorkflowStateEnum.DEV_COMPLETED.is_intermediate() is True
    assert WorkflowStateEnum.ARCH_APPROVED.is_intermediate() is True
    assert WorkflowStateEnum.QA_PASSED.is_intermediate() is True
    assert WorkflowStateEnum.PO_APPROVED.is_intermediate() is True

    assert WorkflowStateEnum.IMPLEMENTING.is_intermediate() is False
    assert WorkflowStateEnum.PENDING_ARCH_REVIEW.is_intermediate() is False


def test_is_waiting_for_role():
    """Test is_waiting_for_role() method.

    This method returns True ONLY for PENDING states (waiting for assignment).
    Active states (IMPLEMENTING, ARCH_REVIEWING, QA_TESTING) return False
    to avoid race conditions in multi-agent teams.
    """
    # Pending states (waiting for role assignment)
    assert WorkflowStateEnum.PENDING_ARCH_REVIEW.is_waiting_for_role() is True
    assert WorkflowStateEnum.PENDING_QA.is_waiting_for_role() is True
    assert WorkflowStateEnum.PENDING_PO_APPROVAL.is_waiting_for_role() is True

    # Active states (already assigned, NOT waiting)
    assert WorkflowStateEnum.IMPLEMENTING.is_waiting_for_role() is False
    assert WorkflowStateEnum.ARCH_REVIEWING.is_waiting_for_role() is False
    assert WorkflowStateEnum.QA_TESTING.is_waiting_for_role() is False

    # Terminal/intermediate states
    assert WorkflowStateEnum.DONE.is_waiting_for_role() is False
    assert WorkflowStateEnum.ARCH_APPROVED.is_waiting_for_role() is False
    assert WorkflowStateEnum.TODO.is_waiting_for_role() is False

