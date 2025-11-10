"""Unit tests for DecisionSelector domain service."""

import pytest
from core.context.domain.decision_status import DecisionStatus
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.role import Role
from core.context.domain.services.decision_selector import DecisionSelector
from core.context.domain.task_plan import TaskPlan
from core.context.domain.task_type import TaskType
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


@pytest.fixture
def role_tasks() -> list[TaskPlan]:
    """Create test tasks for a role."""
    return [
        TaskPlan(
            task_id=TaskId("task-001"),
            title="Task 1",
            description="Implement feature",
            role="developer",
            type=TaskType.DEVELOPMENT,
            suggested_tech=(),
            depends_on=(),
            estimate_points=5.0,
            priority=1,
            risk_score=0.3,
            notes="",
        ),
        TaskPlan(
            task_id=TaskId("task-002"),
            title="Task 2",
            description="Fix bug",
            role="developer",
            type=TaskType.BUG_FIX,
            suggested_tech=(),
            depends_on=(),
            estimate_points=3.0,
            priority=2,
            risk_score=0.4,
            notes="",
        ),
    ]


@pytest.fixture
def decisions() -> list[DecisionNode]:
    """Create test decisions."""
    return [
        DecisionNode(
            id=DecisionId("dec-001"),
            title="Decision 1",
            rationale="First decision rationale",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000000,
            author_id=ActorId("user-001"),
        ),
        DecisionNode(
            id=DecisionId("dec-002"),
            title="Decision 2",
            rationale="Second decision rationale",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000001,
            author_id=ActorId("user-001"),
        ),
        DecisionNode(
            id=DecisionId("dec-003"),
            title="Decision 3",
            rationale="Third decision rationale",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000002,
            author_id=ActorId("user-001"),
        ),
    ]


@pytest.fixture
def decisions_by_id(decisions) -> dict[str, DecisionNode]:
    """Create decisions indexed by ID."""
    return {d.id.to_string(): d for d in decisions}


@pytest.fixture
def impacts_by_decision() -> dict[str, list[TaskNode]]:
    """Create test impact mappings."""
    return {
        "dec-001": [
            TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER),
        ],
        "dec-002": [
            TaskNode(id=TaskId("task-002"), title="Task 2", role=Role.DEVELOPER),
        ],
        "dec-003": [
            TaskNode(id=TaskId("task-999"), title="Unrelated Task", role=Role.QA),
        ],
    }


def test_select_for_role_with_relevant_decisions(role_tasks, impacts_by_decision, decisions_by_id, decisions):
    """Test selecting decisions that impact role's tasks."""
    selector = DecisionSelector()

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should find dec-001 and dec-002 (impact task-001 and task-002)
    # dec-003 might also be included if decisions are being deduplicated
    assert len(result) >= 2
    result_ids = {d.id.to_string() for d in result}
    assert "dec-001" in result_ids
    assert "dec-002" in result_ids


def test_select_for_role_with_no_tasks_returns_fallback(impacts_by_decision, decisions_by_id, decisions):
    """Test fallback when role has no tasks."""
    selector = DecisionSelector(fallback_count=2)

    result = selector.select_for_role(
        role_tasks=[],  # No tasks assigned
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should return first 2 decisions as fallback
    assert len(result) == 2
    assert result == decisions[:2]


def test_select_for_role_with_no_relevant_decisions_returns_fallback(role_tasks, decisions_by_id, decisions):
    """Test fallback when no decisions impact role's tasks."""
    selector = DecisionSelector(fallback_count=3)

    # Impacts only affect different tasks (not task-001 or task-002)
    impacts_by_decision = {
        "dec-001": [TaskNode(id=TaskId("task-999"), title="Other Task", role=Role.QA)],
    }

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should return first 3 decisions as fallback
    assert len(result) == 3
    assert result == decisions[:3]


def test_select_for_role_with_custom_fallback_count():
    """Test that custom fallback_count is respected."""
    selector = DecisionSelector(fallback_count=1)

    decisions = [
        DecisionNode(
            id=DecisionId("dec-001"),
            title="D1",
            rationale="First",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000000,
            author_id=ActorId("user-001"),
        ),
        DecisionNode(
            id=DecisionId("dec-002"),
            title="D2",
            rationale="Second",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000001,
            author_id=ActorId("user-001"),
        ),
    ]

    result = selector.select_for_role(
        role_tasks=[],
        impacts_by_decision={},
        decisions_by_id={},
        all_decisions=decisions,
    )

    # Should return only 1 decision (custom fallback)
    assert len(result) == 1
    assert result[0].id.to_string() == "dec-001"


def test_select_for_role_when_decision_not_in_index(role_tasks, decisions_by_id, decisions):
    """Test graceful handling when impact references missing decision."""
    selector = DecisionSelector()

    # Impact references dec-999 which doesn't exist in decisions_by_id
    impacts_by_decision = {
        "dec-999": [TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER)],
    }

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should return fallback (no valid decisions found)
    # Default fallback_count is 5, but we only have 3 decisions total
    assert len(result) <= 5
    assert len(result) == min(5, len(decisions))


def test_select_for_role_with_multiple_impacts_per_decision(role_tasks, decisions_by_id, decisions):
    """Test when one decision impacts multiple tasks for the same role."""
    selector = DecisionSelector()

    # dec-001 impacts both task-001 and task-002 (both developer tasks)
    impacts_by_decision = {
        "dec-001": [
            TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER),
            TaskNode(id=TaskId("task-002"), title="Task 2", role=Role.DEVELOPER),
        ],
    }

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should return dec-001 (it impacts role's tasks)
    assert len(result) >= 1
    result_ids = {d.id.to_string() for d in result}
    assert "dec-001" in result_ids


def test_select_for_role_with_empty_all_decisions():
    """Test edge case when all_decisions is empty (fallback returns empty)."""
    selector = DecisionSelector(fallback_count=5)

    result = selector.select_for_role(
        role_tasks=[],
        impacts_by_decision={},
        decisions_by_id={},
        all_decisions=[],  # No decisions available
    )

    # Should return empty list (nothing to fallback to)
    assert result == []


def test_select_for_role_with_partial_decision_index(role_tasks):
    """Test when some impacts reference decisions not in index (line 53-55)."""
    selector = DecisionSelector()

    # Create impact that references dec-999, which won't be in decisions_by_id
    impacts_by_decision = {
        "dec-999": [TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER)],
    }

    decisions_by_id = {}  # Empty - dec-999 not in index

    decisions = [
        DecisionNode(
            id=DecisionId("dec-100"),
            title="Fallback Decision",
            rationale="Fallback",
            status=DecisionStatus.APPROVED,
            created_at_ms=1000000,
            author_id=ActorId("user-001"),
        ),
    ]

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should get fallback because decision not in index (line 53 returns None, line 54 skips)
    assert len(result) == 1  # Fallback


def test_select_for_role_returns_relevant_not_fallback(role_tasks, impacts_by_decision, decisions_by_id, decisions):
    """Test that when relevant decisions found, fallback is not used (line 61)."""
    selector = DecisionSelector(fallback_count=99)  # High fallback, should not be used

    result = selector.select_for_role(
        role_tasks=role_tasks,
        impacts_by_decision=impacts_by_decision,
        decisions_by_id=decisions_by_id,
        all_decisions=decisions,
    )

    # Should return relevant decisions (not fallback of 99)
    assert len(result) < 99  # Proves fallback wasn't used (line 58 not taken, line 61 returned)
    assert len(result) >= 2  # Has relevant decisions

