"""Unit tests for WorkflowStateCollection."""

from datetime import datetime

from core.shared.domain import Action, ActionEnum

from services.workflow.domain.collections.workflow_state_collection import (
    WorkflowStateCollection,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def test_collection_filter_ready_for_role():
    """Test filter_ready_for_role() method (Tell, Don't Ask).

    Only PENDING states are considered ready (to avoid multi-agent conflicts).
    Active states (IMPLEMENTING, ARCH_REVIEWING) are NOT included.
    """
    # PENDING state for architect (ready for assignment)
    arch_pending = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
    )

    # ACTIVE state for architect (already assigned, NOT ready)
    arch_active = WorkflowState(
        task_id=TaskId("task-002"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.ARCH_REVIEWING,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 11, 0, 0),
    )

    # ACTIVE state for developer (already assigned, NOT ready)
    dev_active = WorkflowState(
        task_id=TaskId("task-003"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 9, 0, 0),
    )

    # PENDING state for QA (ready for assignment)
    qa_pending = WorkflowState(
        task_id=TaskId("task-004"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_QA,
        role_in_charge=Role.qa(),
        required_action=Action(value=ActionEnum.APPROVE_TESTS),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 12, 0, 0),
    )

    collection = WorkflowStateCollection([arch_pending, arch_active, dev_active, qa_pending])

    # Filter for architect - only PENDING state
    arch_collection = collection.filter_ready_for_role(Role.architect())
    assert len(arch_collection) == 1
    assert arch_pending in arch_collection
    assert arch_active not in arch_collection  # Active state NOT included

    # Filter for developer - no PENDING states
    dev_collection = collection.filter_ready_for_role(Role.developer())
    assert len(dev_collection) == 0  # IMPLEMENTING is NOT ready (already assigned)

    # Filter for QA - only PENDING state
    qa_collection = collection.filter_ready_for_role(Role.qa())
    assert len(qa_collection) == 1
    assert qa_pending in qa_collection


def test_collection_sort_by_priority():
    """Test sort_by_priority() method (rejection count DESC, updated_at ASC)."""
    # State with 2 rejections (high priority)
    from services.workflow.domain.entities.state_transition import StateTransition

    rejection1 = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime(2025, 11, 5, 9, 0, 0),
        feedback="Needs improvement",
    )

    rejection2 = StateTransition(
        from_state="qa_testing",
        to_state="qa_failed",
        action=Action(value=ActionEnum.REJECT_TESTS),
        actor_role=Role.qa(),
        timestamp=datetime(2025, 11, 5, 10, 0, 0),
        feedback="Tests incomplete",
    )

    high_priority = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(rejection1, rejection2),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 12, 0, 0),  # Newer
    )

    # State with 1 rejection (medium priority)
    medium_priority = WorkflowState(
        task_id=TaskId("task-002"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(rejection1,),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 11, 0, 0),  # Older
    )

    # State with 0 rejections (low priority)
    low_priority = WorkflowState(
        task_id=TaskId("task-003"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 8, 0, 0),  # Oldest
    )

    # Unsorted collection
    collection = WorkflowStateCollection([low_priority, high_priority, medium_priority])

    # Sort by priority
    sorted_collection = collection.sort_by_priority()
    sorted_list = sorted_collection.to_list()

    # Priority: rejection count DESC, then updated_at ASC
    assert sorted_list[0] == high_priority  # 2 rejections (highest)
    assert sorted_list[1] == medium_priority  # 1 rejection
    assert sorted_list[2] == low_priority  # 0 rejections


def test_collection_fluent_api():
    """Test fluent API (chainable methods)."""
    state1 = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
    )

    state2 = WorkflowState(
        task_id=TaskId("task-002"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 9, 0, 0),
    )

    collection = WorkflowStateCollection([state1, state2])

    # Fluent API: filter + sort
    result = collection.filter_ready_for_role(Role.architect()).sort_by_priority()

    assert len(result) == 1
    assert result.to_list()[0] == state1


def test_collection_len_and_bool():
    """Test __len__() and __bool__() methods."""
    empty_collection = WorkflowStateCollection([])
    assert len(empty_collection) == 0
    assert bool(empty_collection) is False

    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    non_empty = WorkflowStateCollection([state])
    assert len(non_empty) == 1
    assert bool(non_empty) is True

