"""Tests for approve_review_plan_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases import ApproveReviewPlanUseCase, CeremonyNotFoundError
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.approve_review_plan_handler import (
    approve_review_plan_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock ApproveReviewPlanUseCase."""
    return AsyncMock(spec=ApproveReviewPlanUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def mock_plan():
    """Create a mock plan with plan_id."""
    plan = Mock()
    plan.plan_id.value = "plan-abc123"
    return plan


@pytest.fixture
def sample_review_result():
    """Create a sample review result with PENDING status."""
    return StoryReviewResult(
        story_id=StoryId("story-1"),
        plan_preliminary=None,
        architect_feedback="Architecture looks solid",
        qa_feedback="Tests are comprehensive",
        devops_feedback="Deployment plan is clear",
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_ceremony(sample_review_result):
    """Create a sample ceremony with one review result (exercises status_counts loop)."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        created_by=UserName("architect"),
        story_ids=(StoryId("story-1"), StoryId("story-2")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
        review_results=(sample_review_result,),
    )


@pytest.mark.asyncio
async def test_approve_review_plan_success(
    mock_use_case, mock_context, mock_plan, sample_ceremony
):
    """Test approving review plan successfully with review results (covers status_counts loop)."""
    mock_use_case.execute.return_value = (mock_plan, sample_ceremony)
    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        approved_by="po-user",
        po_notes="LGTM, proceed with implementation",
    )

    response = await approve_review_plan_handler(request, mock_context, mock_use_case)

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is True
    assert "plan-abc123" in response.message
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_review_plan_ceremony_not_found(mock_use_case, mock_context):
    """Test approving plan when ceremony doesn't exist."""
    mock_use_case.execute.side_effect = CeremonyNotFoundError(
        "Ceremony not found: nonexistent"
    )
    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="nonexistent",
        story_id="story-1",
        approved_by="po-user",
        po_notes="Notes",
    )

    response = await approve_review_plan_handler(request, mock_context, mock_use_case)

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is False
    assert "Ceremony not found" in response.message
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_review_plan_validation_error(mock_use_case, mock_context):
    """Test approving plan when the use case raises a validation error."""
    # ValueError from the use case (e.g. story not in ceremony), not from
    # domain object construction — so approved_by and po_notes must be valid.
    mock_use_case.execute.side_effect = ValueError("Story not found in ceremony")
    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-99",
        approved_by="po-user",
        po_notes="Looks good",
    )

    response = await approve_review_plan_handler(request, mock_context, mock_use_case)

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is False
    assert "Story not found in ceremony" in response.message
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_review_plan_internal_error(mock_use_case, mock_context):
    """Test approving plan with an unexpected internal error."""
    mock_use_case.execute.side_effect = Exception("Database connection failed")
    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        approved_by="po-user",
        po_notes="Notes",
    )

    response = await approve_review_plan_handler(request, mock_context, mock_use_case)

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert "Database connection failed" in response.message
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()
