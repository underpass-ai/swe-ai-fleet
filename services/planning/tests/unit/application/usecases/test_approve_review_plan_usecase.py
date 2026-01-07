"""Unit tests for ApproveReviewPlanUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.approve_review_plan_usecase import (
    ApproveReviewPlanUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_approval import PlanApproval
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.review.task_decision import TaskDecision
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


@pytest.fixture
def mock_storage():
    """Mock StoragePort."""
    return AsyncMock()


@pytest.fixture
def mock_messaging():
    """Mock MessagingPort."""
    return AsyncMock()


@pytest.fixture
def use_case(mock_storage, mock_messaging):
    """Create ApproveReviewPlanUseCase instance."""
    return ApproveReviewPlanUseCase(storage=mock_storage, messaging=mock_messaging)


@pytest.fixture
def ceremony_id():
    """Create test ceremony ID."""
    return BacklogReviewCeremonyId("BRC-12345")


@pytest.fixture
def story_id():
    """Create test story ID."""
    return StoryId("ST-001")


@pytest.fixture
def plan_approval():
    """Create test PlanApproval."""
    return PlanApproval(
        approved_by=UserName("po-tirso"),
        po_notes="This plan looks good and aligns with our roadmap",
        po_concerns="Monitor performance during implementation",
        priority_adjustment="HIGH",
        po_priority_reason="Critical for Q1 goals",
    )


@pytest.fixture
def plan_preliminary():
    """Create test PlanPreliminary."""
    return PlanPreliminary(
        title=Title("Plan for User Authentication"),
        description=Brief("Implement JWT-based authentication"),
        acceptance_criteria=("User can login", "User can logout"),
        technical_notes="Use JWT tokens",
        roles=("ARCHITECT", "QA", "DEVOPS"),
        estimated_complexity="MEDIUM",
        dependencies=(),
        tasks_outline=("Setup JWT middleware", "Create login endpoint"),
        task_decisions=(
            TaskDecision(
                task_description="Setup JWT middleware",
                decided_by="ARCHITECT",
                decision_reason="JWT is standard for stateless authentication",
                council_feedback="ARCHITECT: JWT provides secure token-based auth",
                task_index=0,
                decided_at=datetime.now(UTC),
            ),
            TaskDecision(
                task_description="Create login endpoint",
                decided_by="ARCHITECT",
                decision_reason="Need REST endpoint for authentication",
                council_feedback="ARCHITECT: REST endpoint needed for frontend",
                task_index=1,
                decided_at=datetime.now(UTC),
            ),
        ),
    )


@pytest.fixture
def review_result(story_id, plan_preliminary):
    """Create test StoryReviewResult."""
    return StoryReviewResult(
        story_id=story_id,
        plan_preliminary=plan_preliminary,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(),
    )


@pytest.fixture
def ceremony(ceremony_id, story_id, review_result):
    """Create test BacklogReviewCeremony."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=now,
        updated_at=now,
        started_at=now,
        review_results=(review_result,),
    )


@pytest.mark.asyncio
async def test_approve_review_plan_success(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test successful plan approval."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, updated_ceremony = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    assert plan.story_ids == (story_id,)
    assert isinstance(updated_ceremony, BacklogReviewCeremony)

    # Verify storage calls
    mock_storage.get_backlog_review_ceremony.assert_awaited_once_with(
        ceremony.ceremony_id
    )
    mock_storage.save_plan.assert_awaited_once()
    saved_plan = mock_storage.save_plan.call_args[0][0]
    assert isinstance(saved_plan, Plan)
    assert saved_plan.story_ids == (story_id,)

    # Verify tasks were created (2 tasks from task_decisions)
    assert mock_storage.save_task_with_decision.await_count == 2

    # Verify ceremony was saved
    mock_storage.save_backlog_review_ceremony.assert_awaited_once()

    # Verify that updated ceremony has plan_id in review_result
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    assert isinstance(saved_ceremony, BacklogReviewCeremony)
    assert len(saved_ceremony.review_results) == 1
    approved_review_result = saved_ceremony.review_results[0]
    assert approved_review_result.plan_id == plan.plan_id
    assert approved_review_result.approval_status.is_approved()

    # Verify event was published
    mock_messaging.publish.assert_awaited_once()
    publish_call = mock_messaging.publish.call_args
    assert publish_call[1]["subject"] == "planning.plan.approved"
    payload = publish_call[1]["payload"]
    assert payload["ceremony_id"] == ceremony.ceremony_id.value
    assert payload["story_id"] == story_id.value
    assert payload["approved_by"] == plan_approval.approved_by.value
    assert payload["plan_id"] == plan.plan_id.value
    assert payload["tasks_created"] == 2


@pytest.mark.asyncio
async def test_approve_review_plan_ceremony_not_found(
    use_case, mock_storage, ceremony_id, story_id, plan_approval
):
    """Test that CeremonyNotFoundError is raised when ceremony not found."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = None

    # Act & Assert
    with pytest.raises(CeremonyNotFoundError, match="Ceremony not found"):
        await use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )

    mock_storage.get_backlog_review_ceremony.assert_awaited_once_with(ceremony_id)


@pytest.mark.asyncio
async def test_approve_review_plan_story_not_in_ceremony(
    use_case, mock_storage, ceremony, story_id, plan_approval
):
    """Test that ValueError is raised when story not in ceremony."""
    # Arrange
    different_story_id = StoryId("ST-999")
    mock_storage.get_backlog_review_ceremony.return_value = ceremony

    # Act & Assert
    with pytest.raises(ValueError, match="No review result found for story"):
        await use_case.execute(
            ceremony_id=ceremony.ceremony_id,
            story_id=different_story_id,
            approval=plan_approval,
        )


@pytest.mark.asyncio
async def test_approve_review_plan_no_plan_preliminary(
    use_case, mock_storage, ceremony_id, story_id, plan_approval
):
    """Test that ValueError is raised when no plan preliminary exists."""
    # Arrange
    review_result_no_plan = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=None,  # No plan preliminary
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(),
    )

    now = datetime.now(UTC)
    ceremony_no_plan = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=now,
        updated_at=now,
        started_at=now,
        review_results=(review_result_no_plan,),
    )

    mock_storage.get_backlog_review_ceremony.return_value = ceremony_no_plan

    # Act & Assert
    with pytest.raises(ValueError, match="No plan preliminary found"):
        await use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )


@pytest.mark.asyncio
async def test_approve_review_plan_no_task_decisions(
    use_case, mock_storage, mock_messaging, ceremony_id, story_id, plan_approval
):
    """Test plan approval when plan preliminary has no task_decisions."""
    # Arrange
    plan_preliminary_no_tasks = PlanPreliminary(
        title=Title("Plan without tasks"),
        description=Brief("Simple plan"),
        acceptance_criteria=("Criterion 1",),
        technical_notes="",
        roles=("ARCHITECT",),
        estimated_complexity="LOW",
        dependencies=(),
        tasks_outline=(),
        task_decisions=(),  # No task decisions
    )

    review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=plan_preliminary_no_tasks,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(),
    )

    now = datetime.now(UTC)
    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=now,
        updated_at=now,
        started_at=now,
        review_results=(review_result,),
    )

    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, _ = await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    # Verify no tasks were created
    mock_storage.save_task_with_decision.assert_not_awaited()
    # Verify event shows 0 tasks created
    publish_call = mock_messaging.publish.call_args
    payload = publish_call[1]["payload"]
    assert payload["tasks_created"] == 0


@pytest.mark.asyncio
async def test_approve_review_plan_messaging_failure_does_not_raise(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that messaging failure is logged but does not raise exception."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock(side_effect=Exception("NATS connection failed"))

    # Act - should not raise
    plan, updated_ceremony = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert - plan and ceremony should still be returned
    assert isinstance(plan, Plan)
    assert isinstance(updated_ceremony, BacklogReviewCeremony)
    # Verify messaging was attempted
    mock_messaging.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_review_plan_storage_failure_propagates(
    use_case, mock_storage, ceremony, story_id, plan_approval
):
    """Test that storage failure propagates."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock(side_effect=Exception("Storage error"))

    # Act & Assert
    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(
            ceremony_id=ceremony.ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )


@pytest.mark.asyncio
async def test_approve_review_plan_creates_tasks_with_decision_metadata(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that tasks are created with decision metadata."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert - verify task creation calls
    assert mock_storage.save_task_with_decision.await_count == 2

    # Verify first task decision metadata
    first_call = mock_storage.save_task_with_decision.call_args_list[0]
    task = first_call[1]["task"]
    decision_metadata = first_call[1]["decision_metadata"]

    assert task.title == "Setup JWT middleware"  # title is now str, not Title VO
    assert decision_metadata["decided_by"] == "ARCHITECT"
    assert decision_metadata["decision_reason"] == "JWT is standard for stateless authentication"
    assert decision_metadata["source"] == "BACKLOG_REVIEW"
    assert "decided_at" in decision_metadata

    # Verify second task decision metadata
    second_call = mock_storage.save_task_with_decision.call_args_list[1]
    task2 = second_call[1]["task"]
    assert task2.title == "Create login endpoint"  # title is now str, not Title VO


@pytest.mark.asyncio
async def test_approve_review_plan_save_task_failure_propagates(
    use_case, mock_storage, ceremony, story_id, plan_approval
):
    """Test that task save failure propagates."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock(
        side_effect=Exception("Task save error")
    )

    # Act & Assert
    with pytest.raises(Exception, match="Task save error"):
        await use_case.execute(
            ceremony_id=ceremony.ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )


@pytest.mark.asyncio
async def test_approve_review_plan_save_ceremony_failure_propagates(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that ceremony save failure propagates."""
    # Arrange
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock(
        side_effect=Exception("Ceremony save error")
    )
    mock_messaging.publish = AsyncMock()

    # Act & Assert
    with pytest.raises(Exception, match="Ceremony save error"):
        await use_case.execute(
            ceremony_id=ceremony.ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )


@pytest.mark.asyncio
async def test_approve_review_plan_with_priority_adjustment(
    use_case, mock_storage, mock_messaging, ceremony, story_id
):
    """Test plan approval with priority adjustment."""
    # Arrange
    plan_approval_with_priority = PlanApproval(
        approved_by=UserName("po-tirso"),
        po_notes="Approved with priority adjustment",
        po_concerns=None,
        priority_adjustment="HIGH",
        po_priority_reason="Critical for Q1",
    )

    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, _ = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval_with_priority,
    )

    # Assert
    assert isinstance(plan, Plan)
    # Verify priority adjustment is in event payload
    publish_call = mock_messaging.publish.call_args
    payload = publish_call[1]["payload"]
    assert payload["priority_adjustment"] == "HIGH"
    assert payload["po_priority_reason"] == "Critical for Q1"


@pytest.mark.asyncio
async def test_approve_review_plan_with_concerns(
    use_case, mock_storage, mock_messaging, ceremony, story_id
):
    """Test plan approval with PO concerns."""
    # Arrange
    plan_approval_with_concerns = PlanApproval(
        approved_by=UserName("po-tirso"),
        po_notes="Approved but with concerns",
        po_concerns="Monitor performance during implementation",
        priority_adjustment=None,
        po_priority_reason=None,
    )

    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, _ = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval_with_concerns,
    )

    # Assert
    assert isinstance(plan, Plan)
    # Verify concerns are in event payload
    publish_call = mock_messaging.publish.call_args
    payload = publish_call[1]["payload"]
    assert payload["po_concerns"] == "Monitor performance during implementation"


@pytest.mark.asyncio
async def test_approve_review_plan_updates_existing_tasks_with_plan_id(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that approve_review_plan updates existing tasks with plan_id."""
    from planning.domain.entities.task import Task
    from planning.domain.value_objects.identifiers.task_id import TaskId
    from planning.domain.value_objects.statuses.task_status import TaskStatus
    from planning.domain.value_objects.statuses.task_type import TaskType

    # Arrange
    existing_task = Task(
        task_id=TaskId("T-EXISTING"),
        story_id=story_id,
        title="Existing Task",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        plan_id=None,  # No plan_id yet
        description="Existing task description",
        assigned_to="",
        estimated_hours=0,
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
        priority=1,
    )

    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.list_tasks = AsyncMock(return_value=[existing_task])
    mock_storage.save_task = AsyncMock()  # For updating existing task
    mock_storage.save_task_with_decision = AsyncMock()  # For new tasks
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, _ = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    # Verify existing task was updated with plan_id
    mock_storage.save_task.assert_awaited()
    updated_task_call = mock_storage.save_task.await_args[0][0]
    assert updated_task_call.plan_id == plan.plan_id
    assert updated_task_call.task_id == existing_task.task_id


@pytest.mark.asyncio
async def test_approve_review_plan_auto_completes_ceremony(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that approve_review_plan auto-completes ceremony when conditions met."""
    from planning.domain.entities.task import Task
    from planning.domain.value_objects.identifiers.task_id import TaskId
    from planning.domain.value_objects.statuses.task_status import TaskStatus
    from planning.domain.value_objects.statuses.task_type import TaskType

    # Arrange - ceremony with all reviews decided and all stories have tasks
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.list_tasks = AsyncMock(
        return_value=[
            Task(
                task_id=TaskId("T-001"),
                story_id=story_id,
                title="Task 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                plan_id=None,
                description="",
                assigned_to="",
                estimated_hours=0,
                type=TaskType.DEVELOPMENT,
                status=TaskStatus.TODO,
                priority=1,
            )
        ]
    )
    mock_storage.save_task = AsyncMock()
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, updated_ceremony = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    assert isinstance(updated_ceremony, BacklogReviewCeremony)
    # Verify ceremony was saved
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    # Ceremony should be checked for auto-completion
    # (actual completion depends on all conditions being met)
    assert isinstance(saved_ceremony, BacklogReviewCeremony)


@pytest.mark.asyncio
async def test_approve_review_plan_no_auto_complete_when_not_reviewing(
    use_case, mock_storage, mock_messaging, ceremony_id, story_id, plan_approval, review_result
):
    """Test that approve_review_plan doesn't auto-complete when ceremony not in REVIEWING state."""
    from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
        BacklogReviewCeremonyStatus,
        BacklogReviewCeremonyStatusEnum,
    )

    # Arrange - ceremony in COMPLETED state
    completed_ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        review_results=(review_result,),
    )

    mock_storage.get_backlog_review_ceremony.return_value = completed_ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.list_tasks = AsyncMock(return_value=[])
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, updated_ceremony = await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    assert isinstance(updated_ceremony, BacklogReviewCeremony)
    # Ceremony should remain COMPLETED (not re-completed)
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    assert saved_ceremony.status.to_string() == "COMPLETED"


@pytest.mark.asyncio
async def test_approve_review_plan_no_auto_complete_when_stories_missing_tasks(
    use_case, mock_storage, mock_messaging, ceremony, story_id, plan_approval
):
    """Test that approve_review_plan doesn't auto-complete when stories missing tasks."""
    # Arrange - ceremony with story that has no tasks
    mock_storage.get_backlog_review_ceremony.return_value = ceremony
    mock_storage.save_plan = AsyncMock()
    mock_storage.list_tasks = AsyncMock(return_value=[])  # No tasks
    mock_storage.save_task_with_decision = AsyncMock()
    mock_storage.save_backlog_review_ceremony = AsyncMock()
    mock_messaging.publish = AsyncMock()

    # Act
    plan, updated_ceremony = await use_case.execute(
        ceremony_id=ceremony.ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert
    assert isinstance(plan, Plan)
    assert isinstance(updated_ceremony, BacklogReviewCeremony)
    # Ceremony should NOT be auto-completed (stories missing tasks)
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    assert saved_ceremony.status.to_string() == "REVIEWING"  # Still reviewing


@pytest.mark.asyncio
async def test_approve_review_plan_idempotency_already_approved_with_plan_id(
    use_case, mock_storage, mock_messaging, ceremony_id, story_id, plan_approval
):
    """Test idempotency: when plan is already approved with plan_id, returns existing plan."""
    from planning.domain.entities.plan import Plan
    from planning.domain.value_objects.content.brief import Brief
    from planning.domain.value_objects.content.title import Title

    # Arrange - ceremony with already approved review result that has plan_id
    existing_plan_id = PlanId("PL-EXISTING-123")
    approved_review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=PlanPreliminary(
            title=Title("Existing Plan"),
            description=Brief("Existing description"),
            acceptance_criteria=("Criterion 1",),
            technical_notes="Notes",
            roles=("ARCHITECT",),
            estimated_complexity="MEDIUM",
            dependencies=(),
            tasks_outline=(),
        ),
        architect_feedback="Feedback",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
        reviewed_at=datetime.now(UTC),
        approved_by=UserName("po-tirso"),
        approved_at=datetime.now(UTC),
        po_notes="Already approved",
        plan_id=existing_plan_id,
    )

    approved_ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(approved_review_result,),
    )

    existing_plan = Plan(
        plan_id=existing_plan_id,
        story_ids=(story_id,),
        title=Title("Existing Plan"),
        description=Brief("Existing description"),
        acceptance_criteria=("Criterion 1",),
    )

    mock_storage.get_backlog_review_ceremony.return_value = approved_ceremony
    mock_storage.get_plan.return_value = existing_plan

    # Act
    returned_plan, returned_ceremony = await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approval=plan_approval,
    )

    # Assert - should return existing plan without creating new one
    assert returned_plan.plan_id == existing_plan_id
    assert returned_plan.plan_id == existing_plan.plan_id
    assert returned_ceremony == approved_ceremony

    # Verify no new plan was created
    mock_storage.save_plan.assert_not_awaited()
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()
    mock_messaging.publish.assert_not_awaited()

    # Verify existing plan was retrieved
    mock_storage.get_plan.assert_awaited_once_with(existing_plan_id)


@pytest.mark.asyncio
async def test_approve_review_plan_idempotency_already_approved_no_plan_id(
    use_case, mock_storage, mock_messaging, ceremony_id, story_id, plan_approval
):
    """Test idempotency: when plan is already approved but no plan_id, raises ValueError."""
    # Arrange - ceremony with already approved review result but NO plan_id
    approved_review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=PlanPreliminary(
            title=Title("Existing Plan"),
            description=Brief("Existing description"),
            acceptance_criteria=("Criterion 1",),
            technical_notes="Notes",
            roles=("ARCHITECT",),
            estimated_complexity="MEDIUM",
            dependencies=(),
            tasks_outline=(),
        ),
        architect_feedback="Feedback",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
        reviewed_at=datetime.now(UTC),
        approved_by=UserName("po-tirso"),
        approved_at=datetime.now(UTC),
        po_notes="Already approved",
        plan_id=None,  # NO plan_id - indicates Neo4j sync issue
    )

    approved_ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(approved_review_result,),
    )

    mock_storage.get_backlog_review_ceremony.return_value = approved_ceremony

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )

    assert "already APPROVED" in str(exc_info.value)
    assert "no plan_id found" in str(exc_info.value)
    assert "Neo4j synchronization" in str(exc_info.value)

    # Verify no operations were performed
    mock_storage.save_plan.assert_not_awaited()
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_review_plan_idempotency_already_approved_plan_not_found(
    use_case, mock_storage, mock_messaging, ceremony_id, story_id, plan_approval
):
    """Test idempotency: when plan is already approved with plan_id but plan not found, should continue."""
    # Arrange - ceremony with already approved review result that has plan_id
    # but get_plan returns None (plan was deleted or doesn't exist)
    existing_plan_id = PlanId("PL-NOT-FOUND-123")
    approved_review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=PlanPreliminary(
            title=Title("Existing Plan"),
            description=Brief("Existing description"),
            acceptance_criteria=("Criterion 1",),
            technical_notes="Notes",
            roles=("ARCHITECT",),
            estimated_complexity="MEDIUM",
            dependencies=(),
            tasks_outline=(),
        ),
        architect_feedback="Feedback",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
        reviewed_at=datetime.now(UTC),
        approved_by=UserName("po-tirso"),
        approved_at=datetime.now(UTC),
        po_notes="Already approved",
        plan_id=existing_plan_id,
    )

    approved_ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po-tirso"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(approved_review_result,),
    )

    # Plan not found - get_plan returns None
    # This scenario should be handled: if plan_id exists in review_result but plan not found,
    # it means data inconsistency. The code will continue and try to approve again,
    # but review_result.approve() will raise ValueError because status is already APPROVED.
    mock_storage.get_backlog_review_ceremony.return_value = approved_ceremony
    mock_storage.get_plan.return_value = None

    # Act & Assert - should raise ValueError when trying to approve already approved result
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            approval=plan_approval,
        )

    assert "Cannot approve review in status APPROVED" in str(exc_info.value)
    # Verify get_plan was called to check for existing plan
    mock_storage.get_plan.assert_awaited_once_with(existing_plan_id)
