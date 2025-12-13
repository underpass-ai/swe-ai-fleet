"""Get workflow statistics use case.

Calculates workflow metrics and statistics.
Following Hexagonal Architecture.
"""

from datetime import datetime

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


class WorkflowStats:
    """Workflow statistics domain value.

    Immutable container for calculated statistics.
    Following DDD: Value Object pattern.
    """

    def __init__(
        self,
        total_tasks: int,
        tasks_in_progress: int,
        tasks_completed: int,
        tasks_waiting_architect: int,
        tasks_waiting_qa: int,
        tasks_waiting_po: int,
        tasks_by_state: dict[str, int],
        avg_time_in_arch_review_seconds: float,
        avg_time_in_qa_seconds: float,
        total_rejections: int,
        approval_rate: float,
    ) -> None:
        """Initialize statistics.

        Args:
            total_tasks: Total number of tasks
            tasks_in_progress: Tasks currently being worked on
            tasks_completed: Tasks in terminal states
            tasks_waiting_architect: Tasks waiting for architect review
            tasks_waiting_qa: Tasks waiting for QA testing
            tasks_waiting_po: Tasks waiting for PO approval
            tasks_by_state: Count of tasks per state
            avg_time_in_arch_review_seconds: Average time in architect review
            avg_time_in_qa_seconds: Average time in QA
            total_rejections: Total number of rejections
            approval_rate: Percentage approved on first try
        """
        self.total_tasks = total_tasks
        self.tasks_in_progress = tasks_in_progress
        self.tasks_completed = tasks_completed
        self.tasks_waiting_architect = tasks_waiting_architect
        self.tasks_waiting_qa = tasks_waiting_qa
        self.tasks_waiting_po = tasks_waiting_po
        self.tasks_by_state = tasks_by_state
        self.avg_time_in_arch_review_seconds = avg_time_in_arch_review_seconds
        self.avg_time_in_qa_seconds = avg_time_in_qa_seconds
        self.total_rejections = total_rejections
        self.approval_rate = approval_rate


class GetStatsUseCase:
    """Use case for retrieving workflow statistics.

    Used by:
    - gRPC API: GetStats RPC
    - Monitoring: Health checks and observability

    Following Hexagonal Architecture:
    - Depends on ports (interfaces), not concrete implementations
    - Calculates statistics from domain entities
    """

    def __init__(self, repository: WorkflowStateRepositoryPort) -> None:
        """Initialize use case with dependencies.

        Args:
            repository: Workflow state persistence port
        """
        self._repository = repository

    async def execute(
        self,
        story_id: str | None = None,
        role: str | None = None,
    ) -> WorkflowStats:
        """Get workflow statistics.

        Args:
            story_id: Optional story identifier filter
            role: Optional role identifier filter

        Returns:
            WorkflowStats value object with calculated statistics
        """
        # Query all states (with optional filters)
        states = await self._repository.get_all_states(
            story_id=story_id,
            role=role,
        )

        # Calculate statistics
        total_tasks = len(states)

        # Count by state
        tasks_by_state: dict[str, int] = {}
        tasks_in_progress = 0
        tasks_completed = 0
        tasks_waiting_architect = 0
        tasks_waiting_qa = 0
        tasks_waiting_po = 0

        # Track time in states for averages
        arch_review_times: list[float] = []
        qa_times: list[float] = []
        total_rejections = 0
        first_approvals = 0
        total_approvals = 0

        now = datetime.now()

        for state in states:
            state_value = state.get_current_state_value()

            # Count by state
            tasks_by_state[state_value] = tasks_by_state.get(state_value, 0) + 1

            # In progress: active work states
            if state_value in (
                WorkflowStateEnum.IMPLEMENTING.value,
                WorkflowStateEnum.ARCH_REVIEWING.value,
                WorkflowStateEnum.QA_TESTING.value,
            ):
                tasks_in_progress += 1

            # Completed: terminal states
            if state_value in (
                WorkflowStateEnum.DONE.value,
                WorkflowStateEnum.CANCELLED.value,
            ):
                tasks_completed += 1

            # Waiting states
            if state_value == WorkflowStateEnum.PENDING_ARCH_REVIEW.value:
                tasks_waiting_architect += 1
            elif state_value == WorkflowStateEnum.PENDING_QA.value:
                tasks_waiting_qa += 1
            elif state_value == WorkflowStateEnum.PENDING_PO_APPROVAL.value:
                tasks_waiting_po += 1

            # Calculate time in states (for averages)
            if state_value in (
                WorkflowStateEnum.PENDING_ARCH_REVIEW.value,
                WorkflowStateEnum.ARCH_REVIEWING.value,
            ):
                time_in_state = (now - state.updated_at).total_seconds()
                if time_in_state > 0:
                    arch_review_times.append(time_in_state)

            if state_value in (
                WorkflowStateEnum.PENDING_QA.value,
                WorkflowStateEnum.QA_TESTING.value,
            ):
                time_in_state = (now - state.updated_at).total_seconds()
                if time_in_state > 0:
                    qa_times.append(time_in_state)

            # Count rejections and approvals
            rejection_count = state.get_rejection_count()
            total_rejections += rejection_count

            # Check if approved on first try (no rejections and completed)
            if rejection_count == 0 and state_value == WorkflowStateEnum.DONE.value:
                first_approvals += 1
                total_approvals += 1
            elif state_value == WorkflowStateEnum.DONE.value:
                total_approvals += 1

        # Calculate averages
        avg_time_in_arch_review = (
            sum(arch_review_times) / len(arch_review_times)
            if arch_review_times
            else 0.0
        )
        avg_time_in_qa = (
            sum(qa_times) / len(qa_times) if qa_times else 0.0
        )

        # Calculate approval rate
        approval_rate = (
            (first_approvals / total_approvals * 100.0)
            if total_approvals > 0
            else 0.0
        )

        return WorkflowStats(
            total_tasks=total_tasks,
            tasks_in_progress=tasks_in_progress,
            tasks_completed=tasks_completed,
            tasks_waiting_architect=tasks_waiting_architect,
            tasks_waiting_qa=tasks_waiting_qa,
            tasks_waiting_po=tasks_waiting_po,
            tasks_by_state=tasks_by_state,
            avg_time_in_arch_review_seconds=avg_time_in_arch_review,
            avg_time_in_qa_seconds=avg_time_in_qa,
            total_rejections=total_rejections,
            approval_rate=approval_rate,
        )
