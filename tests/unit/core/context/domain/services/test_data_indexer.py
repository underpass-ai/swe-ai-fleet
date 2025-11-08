"""Unit tests for DataIndexer domain service."""

import pytest

from core.context.domain.decision_status import DecisionStatus
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.role import Role
from core.context.domain.services.data_indexer import DataIndexer
from core.context.domain.story import Story
from core.context.domain.task_plan import TaskPlan
from core.context.domain.task_type import TaskType
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


@pytest.fixture
def epic() -> Epic:
    """Create test epic."""
    return Epic(
        epic_id=EpicId("epic-001"),
        title="Test Epic",
        description="Test epic description",
        status=EpicStatus.IN_PROGRESS,
    )


@pytest.fixture
def story() -> Story:
    """Create test story."""
    return Story(
        story_id=StoryId("story-001"),
        name="Test Story",
    )


@pytest.fixture
def plan_with_tasks():
    """Create mock plan with tasks."""
    class MockPlan:
        def __init__(self):
            self.tasks = (
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
                    description="Test feature",
                    role="qa",
                    type=TaskType.TESTING,
                    suggested_tech=(),
                    depends_on=(),
                    estimate_points=3.0,
                    priority=2,
                    risk_score=0.2,
                    notes="",
                ),
                TaskPlan(
                    task_id=TaskId("task-003"),
                    title="Task 3",
                    description="Fix bug",
                    role="developer",
                    type=TaskType.BUG_FIX,
                    suggested_tech=(),
                    depends_on=(),
                    estimate_points=2.0,
                    priority=3,
                    risk_score=0.5,
                    notes="",
                ),
            )
    return MockPlan()


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
    ]


@pytest.fixture
def decision_dependencies() -> list[DecisionEdges]:
    """Create test decision dependencies."""
    return [
        DecisionEdges(
            src_id=DecisionId("dec-001"),
            rel_type=GraphRelationType.DEPENDS_ON,
            dst_id=DecisionId("dec-002"),
        ),
    ]


@pytest.fixture
def decision_impacts() -> list[tuple[str, TaskNode]]:
    """Create test decision impacts."""
    return [
        ("dec-001", TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER)),
        ("dec-002", TaskNode(id=TaskId("task-002"), title="Task 2", role=Role.QA)),
    ]


def test_index_with_full_data(epic, story, plan_with_tasks, decisions, decision_dependencies, decision_impacts):
    """Test indexing with complete data."""
    indexer = DataIndexer()

    result = indexer.index(
        epic=epic,
        story=story,
        redis_plan=plan_with_tasks,
        decisions=decisions,
        decision_dependencies=decision_dependencies,
        decision_impacts=decision_impacts,
    )

    # Assert epic and story
    assert result.epic == epic
    assert result.story == story

    # Assert tasks indexed by role
    assert "developer" in result.subtasks_by_role
    assert "qa" in result.subtasks_by_role
    assert len(result.subtasks_by_role["developer"]) == 2  # task-001, task-003
    assert len(result.subtasks_by_role["qa"]) == 1  # task-002

    # Assert decisions indexed by ID
    assert len(result.decisions_by_id) == 2
    assert DecisionId("dec-001") in result.decisions_by_id
    assert DecisionId("dec-002") in result.decisions_by_id

    # Assert dependencies indexed by source (uses DecisionId as key)
    dec_id = DecisionId("dec-001")
    assert dec_id in result.dependencies_by_source
    assert len(result.dependencies_by_source[dec_id]) == 1

    # Assert impacts indexed by decision
    assert "dec-001" in result.impacts_by_decision
    assert "dec-002" in result.impacts_by_decision
    assert len(result.impacts_by_decision["dec-001"]) == 1
    assert len(result.impacts_by_decision["dec-002"]) == 1

    # Assert all decisions preserved
    assert result.all_decisions == decisions


def test_index_without_plan(epic, story, decisions, decision_dependencies, decision_impacts):
    """Test indexing when story has no plan yet (no tasks)."""
    indexer = DataIndexer()

    result = indexer.index(
        epic=epic,
        story=story,
        redis_plan=None,  # No plan yet
        decisions=decisions,
        decision_dependencies=decision_dependencies,
        decision_impacts=decision_impacts,
    )

    # Tasks should be empty dict (no plan = no tasks)
    assert result.subtasks_by_role == {}

    # Other data should still be indexed
    assert result.epic == epic
    assert result.story == story
    assert len(result.decisions_by_id) == 2


def test_index_raises_if_epic_is_none(story):
    """Test that missing epic raises ValueError (domain invariant)."""
    indexer = DataIndexer()

    with pytest.raises(ValueError, match="Epic is required"):
        indexer.index(
            epic=None,  # Violates domain invariant
            story=story,
            redis_plan=None,
            decisions=[],
            decision_dependencies=[],
            decision_impacts=[],
        )


def test_index_raises_if_story_is_none(epic):
    """Test that missing story raises ValueError (domain invariant)."""
    indexer = DataIndexer()

    with pytest.raises(ValueError, match="Story is required"):
        indexer.index(
            epic=epic,
            story=None,  # Violates domain invariant
            redis_plan=None,
            decisions=[],
            decision_dependencies=[],
            decision_impacts=[],
        )


def test_index_with_empty_decisions(epic, story):
    """Test indexing with no decisions (valid scenario)."""
    indexer = DataIndexer()

    result = indexer.index(
        epic=epic,
        story=story,
        redis_plan=None,
        decisions=[],
        decision_dependencies=[],
        decision_impacts=[],
    )

    assert result.decisions_by_id == {}
    assert result.dependencies_by_source == {}
    assert result.impacts_by_decision == {}
    assert result.all_decisions == []


def test_index_tasks_by_role_with_multiple_roles(plan_with_tasks):
    """Test _index_tasks_by_role groups correctly."""
    result = DataIndexer._index_tasks_by_role(plan_with_tasks)

    assert len(result) == 2  # developer, qa
    assert len(result["developer"]) == 2
    assert len(result["qa"]) == 1


def test_index_tasks_by_role_with_none():
    """Test _index_tasks_by_role returns empty dict when plan is None."""
    result = DataIndexer._index_tasks_by_role(None)

    assert result == {}


def test_index_tasks_by_role_raises_if_plan_has_no_tasks_attribute():
    """Test _index_tasks_by_role raises if plan doesn't have tasks attribute."""
    class InvalidPlan:
        pass  # Missing 'tasks' attribute

    with pytest.raises(ValueError, match="PlanVersion must have 'tasks' attribute"):
        DataIndexer._index_tasks_by_role(InvalidPlan())


def test_index_multiple_dependencies_for_same_source(epic, story, decisions):
    """Test indexing when one decision has multiple dependencies."""
    decision_dependencies = [
        DecisionEdges(
            src_id=DecisionId("dec-001"),
            rel_type=GraphRelationType.DEPENDS_ON,
            dst_id=DecisionId("dec-002"),
        ),
        DecisionEdges(
            src_id=DecisionId("dec-001"),
            rel_type=GraphRelationType.RELATES_TO,
            dst_id=DecisionId("dec-003"),
        ),
    ]

    indexer = DataIndexer()
    result = indexer.index(
        epic=epic,
        story=story,
        redis_plan=None,
        decisions=decisions,
        decision_dependencies=decision_dependencies,
        decision_impacts=[],
    )

    # dec-001 should have 2 dependencies (uses DecisionId as key)
    dec_id = DecisionId("dec-001")
    assert dec_id in result.dependencies_by_source
    assert len(result.dependencies_by_source[dec_id]) == 2


def test_index_multiple_impacts_for_same_decision(epic, story, decisions):
    """Test indexing when one decision impacts multiple tasks."""
    decision_impacts = [
        ("dec-001", TaskNode(id=TaskId("task-001"), title="Task 1", role=Role.DEVELOPER)),
        ("dec-001", TaskNode(id=TaskId("task-002"), title="Task 2", role=Role.DEVELOPER)),
        ("dec-001", TaskNode(id=TaskId("task-003"), title="Task 3", role=Role.QA)),
    ]

    indexer = DataIndexer()
    result = indexer.index(
        epic=epic,
        story=story,
        redis_plan=None,
        decisions=decisions,
        decision_dependencies=[],
        decision_impacts=decision_impacts,
    )

    # dec-001 should impact 3 tasks
    assert len(result.impacts_by_decision["dec-001"]) == 3

