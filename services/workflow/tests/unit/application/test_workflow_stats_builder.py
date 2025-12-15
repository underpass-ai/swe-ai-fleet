"""Unit tests for WorkflowStatsBuilder."""

from datetime import datetime, timedelta

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.application.usecases.get_stats_usecase import WorkflowStatsBuilder
from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def _create_state(
    task_id: str,
    state: WorkflowStateEnum,
    updated_at: datetime,
    history: tuple[StateTransition, ...] = (),
) -> WorkflowState:
    """Helper to create WorkflowState for testing."""
    return WorkflowState(
        task_id=TaskId(task_id),
        story_id=StoryId("story-001"),
        current_state=state,
        role_in_charge=Role.developer() if state != WorkflowStateEnum.DONE else None,
        required_action=Action(value=ActionEnum.COMMIT_CODE) if state != WorkflowStateEnum.DONE else None,
        history=history,
        feedback=None,
        updated_at=updated_at,
    )


def _create_rejection_transition(
    timestamp: datetime,
    feedback: str = "Needs improvement",
) -> StateTransition:
    """Helper to create rejection StateTransition."""
    return StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=timestamp,
        feedback=feedback,
    )


class TestWorkflowStatsBuilder:
    """Test suite for WorkflowStatsBuilder."""

    def test_build_empty_stats(self) -> None:
        """Test building stats with no states."""
        builder = WorkflowStatsBuilder()
        stats = builder.build(total_tasks=0)

        assert stats.total_tasks == 0
        assert stats.tasks_in_progress == 0
        assert stats.tasks_completed == 0
        assert stats.tasks_waiting_architect == 0
        assert stats.tasks_waiting_qa == 0
        assert stats.tasks_waiting_po == 0
        assert stats.tasks_by_state == {}
        assert stats.avg_time_in_arch_review_seconds == pytest.approx(0.0)
        assert stats.avg_time_in_qa_seconds == pytest.approx(0.0)
        assert stats.total_rejections == 0
        assert stats.approval_rate == pytest.approx(0.0)

    def test_count_by_state(self) -> None:
        """Test counting tasks by state."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        state1 = _create_state("task-1", WorkflowStateEnum.IMPLEMENTING, now)
        state2 = _create_state("task-2", WorkflowStateEnum.IMPLEMENTING, now)
        state3 = _create_state("task-3", WorkflowStateEnum.DONE, now)

        builder.add_state(state1)
        builder.add_state(state2)
        builder.add_state(state3)

        stats = builder.build(total_tasks=3)

        assert stats.tasks_by_state[WorkflowStateEnum.IMPLEMENTING.value] == 2
        assert stats.tasks_by_state[WorkflowStateEnum.DONE.value] == 1

    def test_count_tasks_in_progress(self) -> None:
        """Test counting tasks in progress states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        implementing = _create_state("task-1", WorkflowStateEnum.IMPLEMENTING, now)
        arch_reviewing = _create_state("task-2", WorkflowStateEnum.ARCH_REVIEWING, now)
        qa_testing = _create_state("task-3", WorkflowStateEnum.QA_TESTING, now)
        done = _create_state("task-4", WorkflowStateEnum.DONE, now)

        builder.add_state(implementing)
        builder.add_state(arch_reviewing)
        builder.add_state(qa_testing)
        builder.add_state(done)

        stats = builder.build(total_tasks=4)

        assert stats.tasks_in_progress == 3  # implementing, arch_reviewing, qa_testing

    def test_count_tasks_completed(self) -> None:
        """Test counting tasks in completed states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        done = _create_state("task-1", WorkflowStateEnum.DONE, now)
        cancelled = _create_state("task-2", WorkflowStateEnum.CANCELLED, now)
        implementing = _create_state("task-3", WorkflowStateEnum.IMPLEMENTING, now)

        builder.add_state(done)
        builder.add_state(cancelled)
        builder.add_state(implementing)

        stats = builder.build(total_tasks=3)

        assert stats.tasks_completed == 2  # done, cancelled

    def test_count_waiting_states(self) -> None:
        """Test counting tasks in waiting states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        waiting_arch = _create_state("task-1", WorkflowStateEnum.PENDING_ARCH_REVIEW, now)
        waiting_qa = _create_state("task-2", WorkflowStateEnum.PENDING_QA, now)
        waiting_po = _create_state("task-3", WorkflowStateEnum.PENDING_PO_APPROVAL, now)
        implementing = _create_state("task-4", WorkflowStateEnum.IMPLEMENTING, now)

        builder.add_state(waiting_arch)
        builder.add_state(waiting_qa)
        builder.add_state(waiting_po)
        builder.add_state(implementing)

        stats = builder.build(total_tasks=4)

        assert stats.tasks_waiting_architect == 1
        assert stats.tasks_waiting_qa == 1
        assert stats.tasks_waiting_po == 1

    def test_accumulate_arch_review_time_metrics(self) -> None:
        """Test accumulating time metrics for architect review states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # State updated 100 seconds ago
        updated_100s_ago = now - timedelta(seconds=100)
        pending_arch = _create_state(
            "task-1",
            WorkflowStateEnum.PENDING_ARCH_REVIEW,
            updated_100s_ago,
        )

        # State updated 200 seconds ago
        updated_200s_ago = now - timedelta(seconds=200)
        arch_reviewing = _create_state(
            "task-2",
            WorkflowStateEnum.ARCH_REVIEWING,
            updated_200s_ago,
        )

        builder.add_state(pending_arch)
        builder.add_state(arch_reviewing)

        stats = builder.build(total_tasks=2)

        # Average should be (100 + 200) / 2 = 150 (using approx for float comparison)
        assert stats.avg_time_in_arch_review_seconds == pytest.approx(150.0, rel=1e-5)

    def test_accumulate_qa_time_metrics(self) -> None:
        """Test accumulating time metrics for QA states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # State updated 50 seconds ago
        updated_50s_ago = now - timedelta(seconds=50)
        pending_qa = _create_state("task-1", WorkflowStateEnum.PENDING_QA, updated_50s_ago)

        # State updated 150 seconds ago
        updated_150s_ago = now - timedelta(seconds=150)
        qa_testing = _create_state("task-2", WorkflowStateEnum.QA_TESTING, updated_150s_ago)

        builder.add_state(pending_qa)
        builder.add_state(qa_testing)

        stats = builder.build(total_tasks=2)

        # Average should be (50 + 150) / 2 = 100 (using approx for float comparison)
        assert stats.avg_time_in_qa_seconds == pytest.approx(100.0, rel=1e-5)

    def test_ignore_negative_time_in_state(self) -> None:
        """Test that negative time differences are ignored."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # State updated in the future (should be ignored)
        future_time = now + timedelta(seconds=100)
        pending_arch = _create_state(
            "task-1",
            WorkflowStateEnum.PENDING_ARCH_REVIEW,
            future_time,
        )

        # Normal state
        updated_100s_ago = now - timedelta(seconds=100)
        arch_reviewing = _create_state(
            "task-2",
            WorkflowStateEnum.ARCH_REVIEWING,
            updated_100s_ago,
        )

        builder.add_state(pending_arch)
        builder.add_state(arch_reviewing)

        stats = builder.build(total_tasks=2)

        # Only the positive time should be counted (using approx for float comparison)
        assert stats.avg_time_in_arch_review_seconds == pytest.approx(100.0, rel=1e-5)

    def test_count_rejections(self) -> None:
        """Test counting rejections from state history."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # State with 1 rejection
        rejection1 = _create_rejection_transition(now - timedelta(hours=1))
        state_with_rejection = _create_state(
            "task-1",
            WorkflowStateEnum.IMPLEMENTING,
            now,
            history=(rejection1,),
        )

        # State with 2 rejections
        rejection2a = _create_rejection_transition(now - timedelta(hours=2))
        rejection2b = _create_rejection_transition(now - timedelta(hours=1))
        state_with_two_rejections = _create_state(
            "task-2",
            WorkflowStateEnum.IMPLEMENTING,
            now,
            history=(rejection2a, rejection2b),
        )

        # State with no rejections
        state_no_rejections = _create_state("task-3", WorkflowStateEnum.IMPLEMENTING, now)

        builder.add_state(state_with_rejection)
        builder.add_state(state_with_two_rejections)
        builder.add_state(state_no_rejections)

        stats = builder.build(total_tasks=3)

        assert stats.total_rejections == 3  # 1 + 2 + 0

    def test_count_approvals_and_first_approvals(self) -> None:
        """Test counting approvals and first-time approvals."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # Done with no rejections (first approval)
        done_no_rejections = _create_state("task-1", WorkflowStateEnum.DONE, now, history=())

        # Done with rejections (not first approval)
        rejection = _create_rejection_transition(now - timedelta(hours=1))
        done_with_rejections = _create_state(
            "task-2",
            WorkflowStateEnum.DONE,
            now,
            history=(rejection,),
        )

        # Not done (should not count as approval)
        implementing = _create_state("task-3", WorkflowStateEnum.IMPLEMENTING, now)

        builder.add_state(done_no_rejections)
        builder.add_state(done_with_rejections)
        builder.add_state(implementing)

        stats = builder.build(total_tasks=3)

        assert stats.total_rejections == 1  # From done_with_rejections
        # Approval rate should be: first_approvals / total_approvals * 100
        # first_approvals = 1, total_approvals = 2
        assert stats.approval_rate == pytest.approx(50.0)

    def test_approval_rate_zero_when_no_approvals(self) -> None:
        """Test approval rate is zero when no tasks are done."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        implementing = _create_state("task-1", WorkflowStateEnum.IMPLEMENTING, now)
        pending_arch = _create_state("task-2", WorkflowStateEnum.PENDING_ARCH_REVIEW, now)

        builder.add_state(implementing)
        builder.add_state(pending_arch)

        stats = builder.build(total_tasks=2)

        assert stats.approval_rate == pytest.approx(0.0)

    def test_comprehensive_integration(self) -> None:
        """Test comprehensive scenario with multiple states."""
        now = datetime.now()
        builder = WorkflowStatsBuilder()

        # Various states with different characteristics
        implementing = _create_state(
            "task-1",
            WorkflowStateEnum.IMPLEMENTING,
            now - timedelta(minutes=30),
        )

        rejection = _create_rejection_transition(now - timedelta(hours=2))
        arch_reviewing = _create_state(
            "task-2",
            WorkflowStateEnum.ARCH_REVIEWING,
            now - timedelta(hours=1),
            history=(rejection,),
        )

        pending_qa = _create_state(
            "task-3",
            WorkflowStateEnum.PENDING_QA,
            now - timedelta(minutes=45),
        )

        done_first = _create_state("task-4", WorkflowStateEnum.DONE, now, history=())

        cancelled = _create_state("task-5", WorkflowStateEnum.CANCELLED, now, history=())

        builder.add_state(implementing)
        builder.add_state(arch_reviewing)
        builder.add_state(pending_qa)
        builder.add_state(done_first)
        builder.add_state(cancelled)

        stats = builder.build(total_tasks=5)

        # Verify counts
        assert stats.total_tasks == 5
        assert stats.tasks_in_progress == 2  # implementing, arch_reviewing
        assert stats.tasks_completed == 2  # done, cancelled
        assert stats.tasks_waiting_architect == 0
        assert stats.tasks_waiting_qa == 1  # pending_qa
        assert stats.tasks_waiting_po == 0

        # Verify time metrics (arch_reviewing was updated 1 hour ago = 3600 seconds)
        assert stats.avg_time_in_arch_review_seconds == pytest.approx(3600.0, rel=1e-5)
        # pending_qa was updated 45 minutes ago = 2700 seconds
        assert stats.avg_time_in_qa_seconds == pytest.approx(2700.0, rel=1e-5)

        # Verify rejections and approvals
        assert stats.total_rejections == 1
        assert stats.approval_rate == pytest.approx(100.0)

        # Verify state counts
        assert stats.tasks_by_state[WorkflowStateEnum.IMPLEMENTING.value] == 1
        assert stats.tasks_by_state[WorkflowStateEnum.ARCH_REVIEWING.value] == 1
        assert stats.tasks_by_state[WorkflowStateEnum.PENDING_QA.value] == 1
        assert stats.tasks_by_state[WorkflowStateEnum.DONE.value] == 1
        assert stats.tasks_by_state[WorkflowStateEnum.CANCELLED.value] == 1
