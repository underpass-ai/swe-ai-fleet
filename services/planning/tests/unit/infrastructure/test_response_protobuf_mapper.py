"""Unit tests for ResponseProtobufMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain import (
    Brief,
    DORScore,
    Story,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import ResponseProtobufMapper


@pytest.fixture
def sample_story():
    """Create sample story for tests."""
    now = datetime.now(UTC)
    return Story(
        epic_id=EpicId("E-TEST-RESPONSE"),
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_ceremony():
    """Create sample BacklogReviewCeremony for tests."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        created_by=UserName("architect"),
        story_ids=(StoryId("story-1"), StoryId("story-2")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
        review_results=(),
    )


def test_create_story_response_success(sample_story):
    """Test create_story_response with success."""
    response = ResponseProtobufMapper.create_story_response(
        success=True,
        message="Story created",
        story=sample_story,
    )

    assert isinstance(response, planning_pb2.CreateStoryResponse)
    assert response.success is True
    assert response.message == "Story created"
    assert response.story.story_id == "story-123"


def test_create_story_response_error():
    """Test create_story_response with error."""
    response = ResponseProtobufMapper.create_story_response(
        success=False,
        message="Validation error",
        story=None,
    )

    assert isinstance(response, planning_pb2.CreateStoryResponse)
    assert response.success is False
    assert response.message == "Validation error"
    assert not response.HasField("story")


def test_list_stories_response_success(sample_story):
    """Test list_stories_response with stories."""
    response = ResponseProtobufMapper.list_stories_response(
        success=True,
        message="Found 1 story",
        stories=[sample_story],
        total_count=1,
    )

    assert isinstance(response, planning_pb2.ListStoriesResponse)
    assert response.success is True
    assert response.total_count == 1
    assert len(response.stories) == 1
    assert response.stories[0].story_id == "story-123"


def test_list_stories_response_empty():
    """Test list_stories_response with no stories."""
    response = ResponseProtobufMapper.list_stories_response(
        success=True,
        message="No stories found",
        stories=[],
        total_count=0,
    )

    assert response.success is True
    assert response.total_count == 0
    assert len(response.stories) == 0


def test_transition_story_response_success(sample_story):
    """Test transition_story_response with success."""
    response = ResponseProtobufMapper.transition_story_response(
        success=True,
        message="Transitioned to PO_REVIEW",
        story=sample_story,
    )

    assert isinstance(response, planning_pb2.TransitionStoryResponse)
    assert response.success is True
    assert response.message == "Transitioned to PO_REVIEW"
    assert response.story.story_id == "story-123"


def test_transition_story_response_error():
    """Test transition_story_response with error."""
    response = ResponseProtobufMapper.transition_story_response(
        success=False,
        message="Invalid transition",
        story=None,
    )

    assert response.success is False
    assert response.message == "Invalid transition"
    assert not response.HasField("story")


def test_approve_decision_response_success():
    """Test approve_decision_response."""
    response = ResponseProtobufMapper.approve_decision_response(
        success=True,
        message="Decision approved",
    )

    assert isinstance(response, planning_pb2.ApproveDecisionResponse)
    assert response.success is True
    assert response.message == "Decision approved"


def test_approve_decision_response_error():
    """Test approve_decision_response with error."""
    response = ResponseProtobufMapper.approve_decision_response(
        success=False,
        message="Validation error",
    )

    assert response.success is False
    assert response.message == "Validation error"


def test_reject_decision_response_success():
    """Test reject_decision_response."""
    response = ResponseProtobufMapper.reject_decision_response(
        success=True,
        message="Decision rejected",
    )

    assert isinstance(response, planning_pb2.RejectDecisionResponse)
    assert response.success is True
    assert response.message == "Decision rejected"


def test_reject_decision_response_error():
    """Test reject_decision_response with error."""
    response = ResponseProtobufMapper.reject_decision_response(
        success=False,
        message="Validation error",
    )

    assert response.success is False
    assert response.message == "Validation error"


def test_get_backlog_review_ceremony_response_success(sample_ceremony):
    """Test get_backlog_review_ceremony_response with success."""
    response = ResponseProtobufMapper.get_backlog_review_ceremony_response(
        success=True,
        message="Ceremony retrieved",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony retrieved"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert len(response.ceremony.story_ids) == 2


def test_get_backlog_review_ceremony_response_not_found():
    """Test get_backlog_review_ceremony_response when ceremony not found."""
    response = ResponseProtobufMapper.get_backlog_review_ceremony_response(
        success=False,
        message="Ceremony not found: invalid-id",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: invalid-id"
    assert not response.HasField("ceremony")


def test_get_backlog_review_ceremony_response_error():
    """Test get_backlog_review_ceremony_response with internal error."""
    response = ResponseProtobufMapper.get_backlog_review_ceremony_response(
        success=False,
        message="Internal error: database connection failed",
        ceremony=None,
    )

    assert response.success is False
    assert response.message == "Internal error: database connection failed"
    assert not response.HasField("ceremony")


def test_create_backlog_review_ceremony_response_success(sample_ceremony):
    """Test create_backlog_review_ceremony_response with success."""
    response = ResponseProtobufMapper.create_backlog_review_ceremony_response(
        success=True,
        message="Ceremony created: ceremony-123",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony created: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert len(response.ceremony.story_ids) == 2


def test_create_backlog_review_ceremony_response_validation_error():
    """Test create_backlog_review_ceremony_response with validation error."""
    response = ResponseProtobufMapper.create_backlog_review_ceremony_response(
        success=False,
        message="created_by is required",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "created_by is required"
    assert not response.HasField("ceremony")


def test_create_backlog_review_ceremony_response_internal_error():
    """Test create_backlog_review_ceremony_response with internal error."""
    response = ResponseProtobufMapper.create_backlog_review_ceremony_response(
        success=False,
        message="Internal error: database connection failed",
        ceremony=None,
    )

    assert response.success is False
    assert response.message == "Internal error: database connection failed"
    assert not response.HasField("ceremony")


def test_approve_review_plan_response_success(sample_ceremony):
    """Test approve_review_plan_response with success."""
    response = ResponseProtobufMapper.approve_review_plan_response(
        success=True,
        message="Plan approved and created: plan-123",
        ceremony=sample_ceremony,
        plan_id="plan-123",
    )

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is True
    assert response.message == "Plan approved and created: plan-123"
    assert response.plan_id == "plan-123"
    assert response.ceremony.ceremony_id == "ceremony-123"


def test_approve_review_plan_response_ceremony_not_found():
    """Test approve_review_plan_response when ceremony not found."""
    response = ResponseProtobufMapper.approve_review_plan_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
        plan_id="",
    )

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")
    assert response.plan_id == ""


def test_approve_review_plan_response_validation_error():
    """Test approve_review_plan_response with validation error."""
    response = ResponseProtobufMapper.approve_review_plan_response(
        success=False,
        message="approved_by is required",
        ceremony=None,
        plan_id="",
    )

    assert isinstance(response, planning_pb2.ApproveReviewPlanResponse)
    assert response.success is False
    assert response.message == "approved_by is required"
    assert not response.HasField("ceremony")
    assert response.plan_id == ""


def test_approve_review_plan_response_internal_error():
    """Test approve_review_plan_response with internal error."""
    response = ResponseProtobufMapper.approve_review_plan_response(
        success=False,
        message="Internal error: database connection failed",
        ceremony=None,
        plan_id="",
    )

    assert response.success is False
    assert response.message == "Internal error: database connection failed"
    assert not response.HasField("ceremony")
    assert response.plan_id == ""


def test_add_stories_to_review_response_success(sample_ceremony):
    """Test add_stories_to_review_response with success."""
    response = ResponseProtobufMapper.add_stories_to_review_response(
        success=True,
        message="Added 2 stories to ceremony",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.AddStoriesToReviewResponse)
    assert response.success is True
    assert response.message == "Added 2 stories to ceremony"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert len(response.ceremony.story_ids) == 2


def test_add_stories_to_review_response_ceremony_not_found():
    """Test add_stories_to_review_response when ceremony not found."""
    response = ResponseProtobufMapper.add_stories_to_review_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.AddStoriesToReviewResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")


def test_add_stories_to_review_response_validation_error():
    """Test add_stories_to_review_response with validation error."""
    response = ResponseProtobufMapper.add_stories_to_review_response(
        success=False,
        message="story_ids cannot be empty",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.AddStoriesToReviewResponse)
    assert response.success is False
    assert response.message == "story_ids cannot be empty"
    assert not response.HasField("ceremony")


def test_add_stories_to_review_response_internal_error():
    """Test add_stories_to_review_response with internal error."""
    response = ResponseProtobufMapper.add_stories_to_review_response(
        success=False,
        message="Internal error: database connection failed",
        ceremony=None,
    )

    assert response.success is False
    assert response.message == "Internal error: database connection failed"
    assert not response.HasField("ceremony")


def test_reject_review_plan_response_success(sample_ceremony):
    """Test reject_review_plan_response with success."""
    response = ResponseProtobufMapper.reject_review_plan_response(
        success=True,
        message="Plan rejected for story story-1",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is True
    assert response.message == "Plan rejected for story story-1"
    assert response.ceremony.ceremony_id == "ceremony-123"


def test_reject_review_plan_response_ceremony_not_found():
    """Test reject_review_plan_response when ceremony not found."""
    response = ResponseProtobufMapper.reject_review_plan_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")


def test_reject_review_plan_response_validation_error():
    """Test reject_review_plan_response with validation error."""
    response = ResponseProtobufMapper.reject_review_plan_response(
        success=False,
        message="rejection_reason is required",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.RejectReviewPlanResponse)
    assert response.success is False
    assert response.message == "rejection_reason is required"
    assert not response.HasField("ceremony")


def test_reject_review_plan_response_internal_error():
    """Test reject_review_plan_response with internal error."""
    response = ResponseProtobufMapper.reject_review_plan_response(
        success=False,
        message="Internal error: database connection failed",
        ceremony=None,
    )

    assert response.success is False
    assert response.message == "Internal error: database connection failed"
    assert not response.HasField("ceremony")


def test_start_backlog_review_ceremony_response_success(sample_ceremony):
    """Test start_backlog_review_ceremony_response with success."""
    response = ResponseProtobufMapper.start_backlog_review_ceremony_response(
        success=True,
        message="Ceremony started: 6 deliberations submitted",
        ceremony=sample_ceremony,
        total_deliberations_submitted=6,
    )

    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony started: 6 deliberations submitted"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert response.total_deliberations_submitted == 6


def test_start_backlog_review_ceremony_response_ceremony_not_found():
    """Test start_backlog_review_ceremony_response when ceremony not found."""
    response = ResponseProtobufMapper.start_backlog_review_ceremony_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
        total_deliberations_submitted=0,
    )

    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")
    assert response.total_deliberations_submitted == 0


def test_start_backlog_review_ceremony_response_validation_error():
    """Test start_backlog_review_ceremony_response with validation error."""
    response = ResponseProtobufMapper.start_backlog_review_ceremony_response(
        success=False,
        message="Cannot start ceremony: No stories to review",
        ceremony=None,
        total_deliberations_submitted=0,
    )

    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Cannot start ceremony: No stories to review"
    assert not response.HasField("ceremony")
    assert response.total_deliberations_submitted == 0


def test_start_backlog_review_ceremony_response_partial_failure(sample_ceremony):
    """Test start_backlog_review_ceremony_response with partial failures."""
    response = ResponseProtobufMapper.start_backlog_review_ceremony_response(
        success=True,
        message="Ceremony started: 4 deliberations submitted (2 failed)",
        ceremony=sample_ceremony,
        total_deliberations_submitted=4,
    )

    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.total_deliberations_submitted == 4
    assert response.ceremony.ceremony_id == "ceremony-123"


def test_complete_backlog_review_ceremony_response_success(sample_ceremony):
    """Test complete_backlog_review_ceremony_response with success."""
    response = ResponseProtobufMapper.complete_backlog_review_ceremony_response(
        success=True,
        message="Ceremony completed: ceremony-123",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony completed: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"


def test_complete_backlog_review_ceremony_response_not_found():
    """Test complete_backlog_review_ceremony_response when ceremony not found."""
    response = ResponseProtobufMapper.complete_backlog_review_ceremony_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")


def test_complete_backlog_review_ceremony_response_validation_error():
    """Test complete_backlog_review_ceremony_response with validation error."""
    response = ResponseProtobufMapper.complete_backlog_review_ceremony_response(
        success=False,
        message="Cannot complete ceremony: Story story-1 still has pending approval",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "pending approval" in response.message
    assert not response.HasField("ceremony")


def test_cancel_backlog_review_ceremony_response_success(sample_ceremony):
    """Test cancel_backlog_review_ceremony_response with success."""
    response = ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
        success=True,
        message="Ceremony cancelled: ceremony-123",
        ceremony=sample_ceremony,
    )

    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony cancelled: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"


def test_cancel_backlog_review_ceremony_response_not_found():
    """Test cancel_backlog_review_ceremony_response when ceremony not found."""
    response = ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
        success=False,
        message="Ceremony not found: ceremony-invalid",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: ceremony-invalid"
    assert not response.HasField("ceremony")


def test_cancel_backlog_review_ceremony_response_validation_error():
    """Test cancel_backlog_review_ceremony_response with validation error."""
    response = ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
        success=False,
        message="Cannot cancel completed ceremony",
        ceremony=None,
    )

    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Cannot cancel completed ceremony"
    assert not response.HasField("ceremony")

