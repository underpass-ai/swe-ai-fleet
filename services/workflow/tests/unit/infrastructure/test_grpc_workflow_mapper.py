"""Unit tests for GrpcWorkflowMapper."""

from datetime import datetime

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum
from services.workflow.infrastructure.mappers.grpc_workflow_mapper import GrpcWorkflowMapper


# Mock protobuf classes for testing
class MockWorkflowStateResponse:
    """Mock protobuf WorkflowStateResponse."""

    def __init__(self, **kwargs):
        self.task_id = kwargs.get("task_id", "")
        self.story_id = kwargs.get("story_id", "")
        self.current_state = kwargs.get("current_state", "")
        self.role_in_charge = kwargs.get("role_in_charge", "")
        self.required_action = kwargs.get("required_action", "")
        self.feedback = kwargs.get("feedback", "")
        self.updated_at = kwargs.get("updated_at", "")
        self.retry_count = kwargs.get("retry_count", 0)
        self.is_terminal = kwargs.get("is_terminal", False)
        self.is_waiting_for_action = kwargs.get("is_waiting_for_action", False)
        self.rejection_count = kwargs.get("rejection_count", 0)
        self.last_action = kwargs.get("last_action", "")
        self.last_actor_role = kwargs.get("last_actor_role", "")


class MockTaskInfo:
    """Mock protobuf TaskInfo."""

    def __init__(self, **kwargs):
        self.task_id = kwargs.get("task_id", "")
        self.story_id = kwargs.get("story_id", "")
        self.current_state = kwargs.get("current_state", "")
        self.role_in_charge = kwargs.get("role_in_charge", "")
        self.required_action = kwargs.get("required_action", "")
        self.updated_at = kwargs.get("updated_at", "")
        self.feedback = kwargs.get("feedback", "")
        self.retry_count = kwargs.get("retry_count", 0)
        self.rejection_count = kwargs.get("rejection_count", 0)


def test_task_id_from_request():
    """Test task_id_from_request() creates TaskId from string."""
    task_id_str = "task-12345"
    result = GrpcWorkflowMapper.task_id_from_request(task_id_str)

    assert isinstance(result, TaskId)
    assert result.value == task_id_str


def test_task_id_from_request_empty():
    """Test task_id_from_request() raises on empty string."""
    with pytest.raises(ValueError):
        GrpcWorkflowMapper.task_id_from_request("")


def test_role_from_request_developer():
    """Test role_from_request() creates Role from string."""
    role_str = "developer"
    result = GrpcWorkflowMapper.role_from_request(role_str)

    assert isinstance(result, Role)
    assert str(result) == role_str


def test_role_from_request_architect():
    """Test role_from_request() for architect role."""
    result = GrpcWorkflowMapper.role_from_request("architect")
    assert str(result) == "architect"


def test_role_from_request_qa():
    """Test role_from_request() for qa role."""
    result = GrpcWorkflowMapper.role_from_request("qa")
    assert str(result) == "qa"


def test_workflow_state_to_response():
    """Test workflow_state_to_response() converts domain to protobuf."""
    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback="Some feedback",
        updated_at=datetime(2025, 11, 6, 10, 30, 0),
        retry_count=2,
    )

    response = GrpcWorkflowMapper.workflow_state_to_response(
        state=state,
        response_class=MockWorkflowStateResponse,
    )

    assert response.task_id == "task-001"
    assert response.story_id == "story-001"
    assert response.current_state == "implementing"
    assert response.role_in_charge == "developer"
    assert response.required_action == "commit_code"
    assert response.feedback == "Some feedback"
    assert response.retry_count == 2
    assert response.updated_at is not None  # Timestamp protobuf object


def test_workflow_state_to_response_no_role():
    """Test workflow_state_to_response() with no role_in_charge."""
    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 30, 0),
    )

    response = GrpcWorkflowMapper.workflow_state_to_response(
        state=state,
        response_class=MockWorkflowStateResponse,
    )

    assert response.task_id == "task-001"
    assert response.role_in_charge == "no_role"
    assert response.required_action == "no_action"
    assert response.feedback == ""


def test_workflow_states_to_task_list():
    """Test workflow_states_to_task_list() converts multiple states."""
    state1 = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 0, 0),
    )

    state2 = WorkflowState(
        task_id=TaskId("task-002"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 9, 0, 0),
    )

    states = [state1, state2]
    task_infos = GrpcWorkflowMapper.workflow_states_to_task_list(
        states=states,
        task_info_class=MockTaskInfo,
    )

    assert len(task_infos) == 2
    assert task_infos[0].task_id == "task-001"
    assert task_infos[0].current_state == "implementing"
    assert task_infos[1].task_id == "task-002"
    assert task_infos[1].current_state == "pending_arch_review"


def test_workflow_states_to_task_list_empty():
    """Test workflow_states_to_task_list() with empty list."""
    result = GrpcWorkflowMapper.workflow_states_to_task_list(
        states=[],
        task_info_class=MockTaskInfo,
    )

    assert len(result) == 0


def test_workflow_states_to_task_list_with_rejection():
    """Test workflow_states_to_task_list() includes rejection count."""
    from services.workflow.domain.entities.state_transition import StateTransition

    rejection = StateTransition(
        from_state="implementing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime(2025, 11, 6, 9, 0, 0),
        feedback="Needs work",
    )

    state_with_rejection = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(rejection,),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 10, 0, 0),
    )

    states = [state_with_rejection]
    task_infos = GrpcWorkflowMapper.workflow_states_to_task_list(
        states=states,
        task_info_class=MockTaskInfo,
    )

    assert task_infos[0].rejection_count == 1  # 1 rejection

