"""Unit tests for ResponseProtobufMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum, Title, Brief, UserName
from planning.domain.value_objects.identifiers.epic_id import EpicId
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

