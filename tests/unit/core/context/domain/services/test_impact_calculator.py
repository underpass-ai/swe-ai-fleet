"""Unit tests for ImpactCalculator domain service."""

import pytest

from core.context.domain.decision_status import DecisionStatus
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.role import Role
from core.context.domain.services.impact_calculator import ImpactCalculator
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


@pytest.fixture
def relevant_decisions() -> list[DecisionNode]:
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
    ]


@pytest.fixture
def impacts_by_decision() -> dict[str, list[TaskNode]]:
    """Create test impact mappings."""
    return {
        "dec-001": [
            TaskNode(id=TaskId("task-001"), title="Implement feature", role=Role.DEVELOPER),
            TaskNode(id=TaskId("task-002"), title="Write tests", role=Role.QA),
        ],
        "dec-002": [
            TaskNode(id=TaskId("task-003"), title="Fix bug", role=Role.DEVELOPER),
        ],
    }


def test_calculate_for_role_filters_by_role(relevant_decisions, impacts_by_decision):
    """Test that calculator filters impacts by role."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=relevant_decisions,
        impacts_by_decision=impacts_by_decision,
        role="developer",
    )

    # Should return only developer tasks (task-001, task-003)
    assert len(result) == 2
    task_ids = {impact.task_id for impact in result}
    assert TaskId("task-001") in task_ids or "task-001" in task_ids
    assert TaskId("task-003") in task_ids or "task-003" in task_ids
    # QA task excluded
    assert TaskId("task-002") not in task_ids and "task-002" not in task_ids


def test_calculate_for_role_returns_task_impacts(relevant_decisions, impacts_by_decision):
    """Test that results are TaskImpact value objects."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=relevant_decisions,
        impacts_by_decision=impacts_by_decision,
        role="developer",
    )

    # Assert TaskImpact structure
    impact = result[0]
    assert isinstance(impact.decision_id, DecisionId)
    assert isinstance(impact.task_id, TaskId)
    assert isinstance(impact.title, str)


def test_calculate_for_role_with_no_impacts(relevant_decisions):
    """Test when decisions don't impact any tasks."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=relevant_decisions,
        impacts_by_decision={},  # No impacts
        role="developer",
    )

    assert result == []


def test_calculate_for_role_with_no_relevant_decisions(impacts_by_decision):
    """Test when no decisions are relevant."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=[],  # No relevant decisions
        impacts_by_decision=impacts_by_decision,
        role="developer",
    )

    assert result == []


def test_calculate_for_role_with_different_roles(relevant_decisions, impacts_by_decision):
    """Test selecting for QA role."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=relevant_decisions,
        impacts_by_decision=impacts_by_decision,
        role="qa",
    )

    # Should return only QA task (task-002)
    assert len(result) == 1
    assert result[0].task_id == "task-002" or result[0].task_id == TaskId("task-002")
    assert result[0].title == "Write tests"


def test_calculate_for_role_decision_id_preserved(relevant_decisions, impacts_by_decision):
    """Test that decision_id is correctly preserved in results."""
    calculator = ImpactCalculator()

    result = calculator.calculate_for_role(
        relevant_decisions=[relevant_decisions[0]],  # Only dec-001
        impacts_by_decision=impacts_by_decision,
        role="developer",
    )

    assert len(result) == 1
    assert result[0].decision_id == DecisionId("dec-001")


def test_calculate_total_impacts_counts_all(impacts_by_decision):
    """Test calculate_total_impacts sums all impact relationships."""
    calculator = ImpactCalculator()

    total = calculator.calculate_total_impacts(impacts_by_decision)

    # dec-001: 2 tasks, dec-002: 1 task = 3 total
    assert total == 3


def test_calculate_total_impacts_with_empty_map():
    """Test calculate_total_impacts with no impacts."""
    calculator = ImpactCalculator()

    total = calculator.calculate_total_impacts({})

    assert total == 0


def test_calculate_total_impacts_with_multiple_decisions():
    """Test calculate_total_impacts with many decisions."""
    calculator = ImpactCalculator()

    impacts_by_decision = {
        "dec-001": [TaskNode(id=TaskId("t1"), title="T1", role=Role.DEVELOPER)],
        "dec-002": [
            TaskNode(id=TaskId("t2"), title="T2", role=Role.DEVELOPER),
            TaskNode(id=TaskId("t3"), title="T3", role=Role.QA),
        ],
        "dec-003": [],  # No impacts
        "dec-004": [
            TaskNode(id=TaskId("t4"), title="T4", role=Role.DEVELOPER),
            TaskNode(id=TaskId("t5"), title="T5", role=Role.DEVELOPER),
            TaskNode(id=TaskId("t6"), title="T6", role=Role.ARCHITECT),
        ],
    }

    total = calculator.calculate_total_impacts(impacts_by_decision)

    # 1 + 2 + 0 + 3 = 6
    assert total == 6

