"""Workflow state metadata service.

Provides metadata about workflow states (responsible role, expected action).
Following Domain-Driven Design principles.
"""

from core.agents_and_tools.agents.domain.entities.rbac.action import Action, ActionEnum
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


class WorkflowStateMetadata:
    """Domain service for workflow state metadata.

    Encapsulates knowledge about:
    - Which role is responsible for each state
    - Which action is expected in each state

    Following DDD:
    - Domain service (stateless)
    - Rich domain model (knows state → role/action mappings)
    - Returns value objects (Role, Action), not primitives
    """

    # Role ownership mapping (immutable class constants)
    _ROLE_MAPPING = {
        WorkflowStateEnum.TODO: None,
        WorkflowStateEnum.IMPLEMENTING: Role.developer(),
        WorkflowStateEnum.DEV_COMPLETED: None,
        WorkflowStateEnum.PENDING_ARCH_REVIEW: Role.architect(),
        WorkflowStateEnum.ARCH_REVIEWING: Role.architect(),
        WorkflowStateEnum.ARCH_APPROVED: None,
        WorkflowStateEnum.ARCH_REJECTED: Role.developer(),
        WorkflowStateEnum.PENDING_QA: Role.qa(),
        WorkflowStateEnum.QA_TESTING: Role.qa(),
        WorkflowStateEnum.QA_PASSED: None,
        WorkflowStateEnum.QA_FAILED: Role.developer(),
        WorkflowStateEnum.PENDING_PO_APPROVAL: Role.po(),
        WorkflowStateEnum.PO_APPROVED: None,
        WorkflowStateEnum.DONE: None,
        WorkflowStateEnum.CANCELLED: None,
    }

    # Expected action mapping (immutable class constants)
    _ACTION_MAPPING = {
        WorkflowStateEnum.TODO: None,
        WorkflowStateEnum.IMPLEMENTING: Action(value=ActionEnum.COMMIT_CODE),
        WorkflowStateEnum.DEV_COMPLETED: None,
        WorkflowStateEnum.PENDING_ARCH_REVIEW: Action(value=ActionEnum.APPROVE_DESIGN),
        WorkflowStateEnum.ARCH_REVIEWING: Action(value=ActionEnum.APPROVE_DESIGN),
        WorkflowStateEnum.ARCH_APPROVED: None,
        WorkflowStateEnum.ARCH_REJECTED: Action(value=ActionEnum.REVISE_CODE),
        WorkflowStateEnum.PENDING_QA: Action(value=ActionEnum.APPROVE_TESTS),
        WorkflowStateEnum.QA_TESTING: Action(value=ActionEnum.APPROVE_TESTS),
        WorkflowStateEnum.QA_PASSED: None,
        WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.REVISE_CODE),
        WorkflowStateEnum.PENDING_PO_APPROVAL: Action(value=ActionEnum.APPROVE_STORY),
        WorkflowStateEnum.PO_APPROVED: None,
        WorkflowStateEnum.DONE: None,
        WorkflowStateEnum.CANCELLED: None,
    }

    @classmethod
    def get_responsible_role(cls, state: WorkflowStateEnum) -> Role | None:
        """Get the role responsible for a workflow state.

        Domain knowledge: State → Role mapping.

        Args:
            state: Workflow state

        Returns:
            Role value object, or None if system/terminal state
        """
        return cls._ROLE_MAPPING.get(state)

    @classmethod
    def get_expected_action(cls, state: WorkflowStateEnum) -> Action | None:
        """Get the expected action for a workflow state.

        Domain knowledge: State → Action mapping.

        Args:
            state: Workflow state

        Returns:
            Action value object, or None if terminal/auto state
        """
        return cls._ACTION_MAPPING.get(state)

