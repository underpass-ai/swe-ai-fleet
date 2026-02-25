"""Tests for reject_review_plan_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases import CeremonyNotFoundError
from planning.application.usecases.reject_review_plan_usecase import (
    RejectReviewPlanUseCase,
)
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
from planning.infrastructure.grpc.handlers.reject_review_plan_handler import (
    reject_review_plan_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock RejectReviewPlanUseCase."""
    return AsyncMock(spec=RejectReviewPlanUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_review_result():
    """Create a sample review result with PENDING status."""
    return StoryReviewResult(
        story_id=StoryId("story-1"),
        plan_preliminary=None,
        architect_feedback="Looks good",
        qa_feedback="Looks good",
        devops_feedback="Looks good",
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
async def test_reject_review_plan_success(
    mock_use_case, mock_context, sample_ceremony
):
    """Test rejecting review plan successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_ceremony
    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="Missing security considerations",
    )

    # Act
    response = await reject_review_plan_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is True
    assert response.message == "Plan rejected for story story-1"
    assert response.ceremony.ceremony_id == "ceremony-123"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_review_plan_ceremony_not_found(mock_use_case, mock_context):
    """Test rejecting plan when ceremony doesn't exist."""
    # Arrange
    mock_use_case.execute.side_effect = CeremonyNotFoundError(
        "Ceremony not found: nonexistent"
    )
    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="nonexistent",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="Reason",
    )

    # Act
    response = await reject_review_plan_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is False
    assert "Ceremony not found" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_review_plan_validation_error(mock_use_case, mock_context):
    """Test rejecting plan with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("rejection_reason cannot be empty")
    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="",
    )

    # Act
    response = await reject_review_plan_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is False
    assert "rejection_reason cannot be empty" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_review_plan_internal_error(mock_use_case, mock_context):
    """Test reject plan with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="Not good enough",
    )

    # Act
    response = await reject_review_plan_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert "Database error" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()

