"""Unit tests for WorkflowStateMetadata domain service."""

from core.shared.domain import Action, ActionEnum

from services.workflow.domain.services.workflow_state_metadata import (
    WorkflowStateMetadata,
)
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def test_get_responsible_role_for_developer_states():
    """Test get_responsible_role() returns developer for dev states."""
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.IMPLEMENTING) == Role.developer()
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.ARCH_REJECTED) == Role.developer()
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.QA_FAILED) == Role.developer()


def test_get_responsible_role_for_architect_states():
    """Test get_responsible_role() returns architect for arch states."""
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.PENDING_ARCH_REVIEW) == Role.architect()
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.ARCH_REVIEWING) == Role.architect()


def test_get_responsible_role_for_qa_states():
    """Test get_responsible_role() returns qa for qa states."""
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.PENDING_QA) == Role.qa()
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.QA_TESTING) == Role.qa()


def test_get_responsible_role_for_po_states():
    """Test get_responsible_role() returns po for po states."""
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.PENDING_PO_APPROVAL) == Role.po()


def test_get_responsible_role_for_system_states():
    """Test get_responsible_role() returns None for system/terminal states."""
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.TODO) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.DEV_COMPLETED) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.ARCH_APPROVED) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.QA_PASSED) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.PO_APPROVED) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.DONE) is None
    assert WorkflowStateMetadata.get_responsible_role(WorkflowStateEnum.CANCELLED) is None


def test_get_expected_action_for_states():
    """Test get_expected_action() returns correct actions."""
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.IMPLEMENTING) == Action(value=ActionEnum.COMMIT_CODE)
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.PENDING_ARCH_REVIEW) == Action(value=ActionEnum.APPROVE_DESIGN)
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.ARCH_REJECTED) == Action(value=ActionEnum.REVISE_CODE)
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.PENDING_QA) == Action(value=ActionEnum.APPROVE_TESTS)
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.PENDING_PO_APPROVAL) == Action(value=ActionEnum.APPROVE_STORY)


def test_get_expected_action_for_terminal_states():
    """Test get_expected_action() returns None for terminal/auto states."""
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.TODO) is None
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.DEV_COMPLETED) is None
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.DONE) is None
    assert WorkflowStateMetadata.get_expected_action(WorkflowStateEnum.CANCELLED) is None

