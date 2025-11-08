"""Unit tests for WorkflowStateMapper.

Tests serialization/deserialization of WorkflowState to/from JSON.
"""

import json
from datetime import datetime

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum
from services.workflow.infrastructure.mappers.workflow_state_mapper import (
    WorkflowStateMapper,
)


@pytest.fixture
def workflow_state_with_history() -> WorkflowState:
    """Create WorkflowState with transitions."""
    transition1 = StateTransition(
        from_state="todo",
        to_state="implementing",
        action=Action(value=ActionEnum.CLAIM_TASK),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 6, 10, 0, 0),
        feedback=None,
    )

    transition2 = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 6, 11, 0, 0),
        feedback="Implementation complete",
    )

    return WorkflowState(
        task_id=TaskId("task-123"),
        story_id=StoryId("story-456"),
        current_state=WorkflowStateEnum.DEV_COMPLETED,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.CLAIM_REVIEW),
        history=(transition1, transition2),
        feedback="Implementation complete",
        updated_at=datetime(2025, 11, 6, 11, 0, 0),
        retry_count=0,
    )


@pytest.fixture
def workflow_state_minimal() -> WorkflowState:
    """Create minimal WorkflowState (no history, no optional fields)."""
    return WorkflowState(
        task_id=TaskId("task-789"),
        story_id=StoryId("story-999"),
        current_state=WorkflowStateEnum.TODO,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.CLAIM_TASK),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 6, 9, 0, 0),
        retry_count=0,
    )


def test_to_json_with_history(workflow_state_with_history: WorkflowState):
    """Test serialization of WorkflowState with transitions."""
    json_str = WorkflowStateMapper.to_json(workflow_state_with_history)

    # Parse JSON
    data = json.loads(json_str)

    # Assert structure
    assert data["task_id"] == "task-123"
    assert data["story_id"] == "story-456"
    assert data["current_state"] == "dev_completed"
    assert data["role_in_charge"] == "architect"
    assert data["required_action"] == "claim_review"
    assert data["feedback"] == "Implementation complete"
    assert data["retry_count"] == 0
    assert "updated_at" in data

    # Assert history
    assert len(data["history"]) == 2
    assert data["history"][0]["from_state"] == "todo"
    assert data["history"][0]["to_state"] == "implementing"
    assert data["history"][0]["action"] == "claim_task"
    assert data["history"][0]["actor_role"] == "developer"
    assert data["history"][0]["feedback"] is None

    assert data["history"][1]["from_state"] == "implementing"
    assert data["history"][1]["to_state"] == "dev_completed"
    assert data["history"][1]["action"] == "commit_code"
    assert data["history"][1]["actor_role"] == "developer"
    assert data["history"][1]["feedback"] == "Implementation complete"


def test_to_json_minimal(workflow_state_minimal: WorkflowState):
    """Test serialization of minimal WorkflowState."""
    json_str = WorkflowStateMapper.to_json(workflow_state_minimal)

    data = json.loads(json_str)

    assert data["task_id"] == "task-789"
    assert data["story_id"] == "story-999"
    assert data["current_state"] == "todo"
    assert data["role_in_charge"] == "developer"
    assert data["required_action"] == "claim_task"
    assert data["feedback"] is None
    assert data["retry_count"] == 0
    assert data["history"] == []


def test_from_json_with_history(workflow_state_with_history: WorkflowState):
    """Test deserialization of WorkflowState with transitions."""
    # Serialize
    json_str = WorkflowStateMapper.to_json(workflow_state_with_history)

    # Deserialize
    restored = WorkflowStateMapper.from_json(json_str)

    # Assert entity equality
    assert restored.task_id == workflow_state_with_history.task_id
    assert restored.story_id == workflow_state_with_history.story_id
    assert restored.current_state == workflow_state_with_history.current_state
    assert restored.role_in_charge == workflow_state_with_history.role_in_charge
    assert restored.required_action == workflow_state_with_history.required_action
    assert restored.feedback == workflow_state_with_history.feedback
    assert restored.retry_count == workflow_state_with_history.retry_count
    assert len(restored.history) == 2

    # Assert transitions
    t1 = restored.history[0]
    assert t1.from_state == "todo"
    assert t1.to_state == "implementing"
    assert t1.action.value == ActionEnum.CLAIM_TASK
    assert str(t1.actor_role) == "developer"

    t2 = restored.history[1]
    assert t2.from_state == "implementing"
    assert t2.to_state == "dev_completed"
    assert t2.action.value == ActionEnum.COMMIT_CODE
    assert str(t2.actor_role) == "developer"
    assert t2.feedback == "Implementation complete"


def test_from_json_minimal(workflow_state_minimal: WorkflowState):
    """Test deserialization of minimal WorkflowState."""
    json_str = WorkflowStateMapper.to_json(workflow_state_minimal)
    restored = WorkflowStateMapper.from_json(json_str)

    assert restored.task_id == workflow_state_minimal.task_id
    assert restored.story_id == workflow_state_minimal.story_id
    assert restored.current_state == workflow_state_minimal.current_state
    assert restored.role_in_charge == workflow_state_minimal.role_in_charge
    assert restored.required_action == workflow_state_minimal.required_action
    assert restored.feedback is None
    assert restored.retry_count == 0
    assert restored.history == ()


def test_from_json_with_bytes():
    """Test deserialization from bytes (Valkey returns bytes)."""
    json_str = (
        '{"task_id": "task-1", "story_id": "story-1", "current_state": "todo", '
        '"role_in_charge": "developer", "required_action": "claim_task", '
        '"feedback": null, "retry_count": 0, "history": [], '
        '"updated_at": "2025-11-06T10:00:00"}'
    )
    json_bytes = json_str.encode("utf-8")

    state = WorkflowStateMapper.from_json(json_bytes)

    assert str(state.task_id) == "task-1"
    assert str(state.story_id) == "story-1"
    assert state.current_state == WorkflowStateEnum.TODO


def test_from_json_invalid_json():
    """Test that invalid JSON raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        WorkflowStateMapper.from_json("not valid json")


def test_from_json_invalid_enum():
    """Test that invalid enum value raises ValueError."""
    invalid_json = (
        '{"task_id": "task-1", "story_id": "story-1", '
        '"current_state": "invalid_state", "role_in_charge": "developer", '
        '"required_action": "claim_task", "feedback": null, "retry_count": 0, '
        '"history": [], "updated_at": "2025-11-06T10:00:00"}'
    )

    with pytest.raises(ValueError):
        WorkflowStateMapper.from_json(invalid_json)


def test_roundtrip_preserves_data(workflow_state_with_history: WorkflowState):
    """Test that serialize → deserialize preserves all data."""
    json_str = WorkflowStateMapper.to_json(workflow_state_with_history)
    restored = WorkflowStateMapper.from_json(json_str)
    json_str2 = WorkflowStateMapper.to_json(restored)

    # JSON should be identical
    assert json.loads(json_str) == json.loads(json_str2)

