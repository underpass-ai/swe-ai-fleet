"""Unit tests for WorkflowStateMachine."""

from datetime import datetime

import pytest

from core.agents_and_tools.agents.domain.entities.rbac.action import Action, ActionEnum
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.exceptions.workflow_transition_error import (
    WorkflowTransitionError,
)
from services.workflow.domain.services.workflow_state_machine import WorkflowStateMachine
from services.workflow.domain.services.workflow_transition_rules import (
    WorkflowTransitionRules,
)
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@pytest.fixture
def fsm_config() -> dict:
    """FSM configuration fixture (simplified).

    Format expected by WorkflowTransitionRules:
    {
        "states": [{"id": "...", "allowed_roles": [...]}],
        "transitions": [{"from": "...", "to": "...", "action": "..."}]
    }
    """
    return {
        "states": [
            #allowed_roles = who can act FROM this state
            {"id": "todo", "allowed_roles": ["developer"]},  # developer can claim
            {"id": "implementing", "allowed_roles": ["developer"]},  # developer can commit
            {"id": "dev_completed", "allowed_roles": ["system"], "auto_transition_to": "pending_arch_review"},
            {"id": "pending_arch_review", "allowed_roles": ["architect"]},  # architect can approve/reject
            {"id": "arch_reviewing", "allowed_roles": ["architect"]},
            {"id": "arch_approved", "allowed_roles": ["system"], "auto_transition_to": "pending_qa"},
            {"id": "arch_rejected", "allowed_roles": ["developer"]},  # developer can revise
            {"id": "pending_qa", "allowed_roles": ["qa"]},  # qa can approve/reject
            {"id": "qa_testing", "allowed_roles": ["qa"]},
            {"id": "qa_passed", "allowed_roles": ["system"], "auto_transition_to": "done"},
            {"id": "qa_failed", "allowed_roles": ["developer"]},  # developer can revise
            {"id": "done", "allowed_roles": []},
        ],
        "transitions": [
            # Action values are snake_case (enum values, not names)
            {"from": "todo", "to": "implementing", "action": "claim_task"},
            {"from": "implementing", "to": "dev_completed", "action": "commit_code"},
            {"from": "dev_completed", "to": "pending_arch_review", "action": "request_review", "auto": True},
            {"from": "pending_arch_review", "to": "arch_approved", "action": "approve_design"},
            {"from": "pending_arch_review", "to": "arch_rejected", "action": "reject_design"},
            {"from": "arch_approved", "to": "pending_qa", "action": "request_review", "auto": True},
            {"from": "arch_rejected", "to": "implementing", "action": "revise_code"},
            {"from": "pending_qa", "to": "qa_passed", "action": "approve_tests"},
            {"from": "pending_qa", "to": "qa_failed", "action": "reject_tests"},
            {"from": "qa_passed", "to": "done", "action": "request_review", "auto": True},
            {"from": "qa_failed", "to": "implementing", "action": "revise_code"},
        ],
    }


@pytest.fixture
def fsm(fsm_config: dict) -> WorkflowStateMachine:
    """WorkflowStateMachine fixture."""
    rules = WorkflowTransitionRules(fsm_config)
    return WorkflowStateMachine(rules)


@pytest.fixture
def base_state() -> WorkflowState:
    """Base WorkflowState fixture (TODO state)."""
    return WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.TODO,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 0, 0),
    )


def test_execute_transition_happy_path(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test successful transition (developer claims task)."""
    action = Action(value=ActionEnum.CLAIM_TASK)
    actor_role = Role.developer()
    timestamp = datetime(2025, 11, 6, 10, 5, 0)

    new_state = fsm.execute_transition(
        current_state=base_state,
        action=action,
        actor_role=actor_role,
        timestamp=timestamp,
        feedback=None,
    )

    # Assertions
    assert new_state.current_state == WorkflowStateEnum.IMPLEMENTING
    assert new_state.role_in_charge == Role.developer()
    assert new_state.required_action == Action(value=ActionEnum.COMMIT_CODE)
    assert len(new_state.history) == 1
    assert new_state.history[0].action == action
    assert new_state.history[0].actor_role == actor_role
    assert new_state.updated_at == timestamp


def test_execute_transition_wrong_role(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test transition fails when wrong role tries to act."""
    action = Action(value=ActionEnum.CLAIM_TASK)
    actor_role = Role.architect()  # Wrong role (should be developer)
    timestamp = datetime(2025, 11, 6, 10, 5, 0)

    with pytest.raises(WorkflowTransitionError) as exc_info:
        fsm.execute_transition(
            current_state=base_state,
            action=action,
            actor_role=actor_role,
            timestamp=timestamp,
            feedback=None,
        )

    assert "not allowed" in str(exc_info.value).lower()


def test_execute_transition_invalid_action(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test transition fails when action not allowed in current state."""
    action = Action(value=ActionEnum.COMMIT_CODE)  # Not allowed in TODO state
    actor_role = Role.developer()
    timestamp = datetime(2025, 11, 6, 10, 5, 0)

    with pytest.raises(WorkflowTransitionError) as exc_info:
        fsm.execute_transition(
            current_state=base_state,
            action=action,
            actor_role=actor_role,
            timestamp=timestamp,
            feedback=None,
        )

    assert "not allowed" in str(exc_info.value).lower()


def test_execute_transition_with_feedback(fsm: WorkflowStateMachine):
    """Test rejection transition with feedback."""
    # Create state in PENDING_ARCH_REVIEW
    arch_review_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 0, 0),
    )

    action = Action(value=ActionEnum.REJECT_DESIGN)
    actor_role = Role.architect()
    timestamp = datetime(2025, 11, 6, 10, 5, 0)
    feedback = "Architecture needs improvement"

    new_state = fsm.execute_transition(
        current_state=arch_review_state,
        action=action,
        actor_role=actor_role,
        timestamp=timestamp,
        feedback=feedback,
    )

    # Assertions
    assert new_state.current_state == WorkflowStateEnum.ARCH_REJECTED
    assert new_state.feedback == feedback
    assert len(new_state.history) == 1
    assert new_state.history[0].feedback == feedback


def test_can_execute_action_true(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test can_execute_action() returns True for valid transition."""
    action = Action(value=ActionEnum.CLAIM_TASK)
    actor_role = Role.developer()

    assert fsm.can_execute_action(base_state, action, actor_role) is True


def test_can_execute_action_false_wrong_role(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test can_execute_action() returns False for wrong role."""
    action = Action(value=ActionEnum.CLAIM_TASK)
    actor_role = Role.architect()  # Wrong role

    assert fsm.can_execute_action(base_state, action, actor_role) is False


def test_can_execute_action_false_invalid_action(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test can_execute_action() returns False for invalid action."""
    action = Action(value=ActionEnum.COMMIT_CODE)  # Not allowed in TODO
    actor_role = Role.developer()

    assert fsm.can_execute_action(base_state, action, actor_role) is False


def test_get_allowed_actions_for_role(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test get_allowed_actions_for_role() returns correct actions."""
    allowed = fsm.get_allowed_actions_for_role(base_state, "developer")

    assert len(allowed) == 1
    assert allowed[0] == Action(value=ActionEnum.CLAIM_TASK)


def test_get_allowed_actions_for_role_terminal_state(fsm: WorkflowStateMachine):
    """Test get_allowed_actions_for_role() returns empty list for terminal state."""
    done_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 0, 0),
    )

    allowed = fsm.get_allowed_actions_for_role(done_state, "developer")
    assert len(allowed) == 0


def test_execute_transition_chain(fsm: WorkflowStateMachine, base_state: WorkflowState):
    """Test multiple transitions in sequence (full workflow).

    Note: Auto-transitions happen automatically, so intermediate states
    like DEV_COMPLETED are skipped.
    """
    # 1. Developer claims task
    state1 = fsm.execute_transition(
        current_state=base_state,
        action=Action(value=ActionEnum.CLAIM_TASK),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 6, 10, 0, 0),
        feedback=None,
    )
    assert state1.current_state == WorkflowStateEnum.IMPLEMENTING

    # 2. Developer completes implementation
    # Auto-transition: DEV_COMPLETED → PENDING_ARCH_REVIEW (automatic)
    state2 = fsm.execute_transition(
        current_state=state1,
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 6, 11, 0, 0),
        feedback=None,
    )
    assert state2.current_state == WorkflowStateEnum.PENDING_ARCH_REVIEW  # Auto-transitioned

    # 3. Architect approves
    # Auto-transition: ARCH_APPROVED → PENDING_QA (automatic)
    state3 = fsm.execute_transition(
        current_state=state2,
        action=Action(value=ActionEnum.APPROVE_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime(2025, 11, 6, 12, 0, 0),
        feedback=None,
    )
    assert state3.current_state == WorkflowStateEnum.PENDING_QA  # Auto-transitioned

    # 4. QA approves
    # Auto-transition: QA_PASSED → DONE (automatic)
    state4 = fsm.execute_transition(
        current_state=state3,
        action=Action(value=ActionEnum.APPROVE_TESTS),
        actor_role=Role.qa(),
        timestamp=datetime(2025, 11, 6, 13, 0, 0),
        feedback=None,
    )
    assert state4.current_state == WorkflowStateEnum.DONE  # Auto-transitioned to terminal

    # Verify history includes auto-transitions
    # Expected: CLAIM_TASK, COMMIT_CODE, REQUEST_REVIEW (auto), APPROVE_DESIGN, REQUEST_REVIEW (auto), APPROVE_TESTS, REQUEST_REVIEW (auto)
    assert len(state4.history) >= 6  # At least 6 transitions (including auto)

