"""Unit tests for EventPayloadMapper."""

from datetime import datetime

from planning.domain import (
    Comment,
    DecisionId,
    Reason,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.infrastructure.mappers.event_payload_mapper import EventPayloadMapper


def test_story_created_payload():
    """Test story_created_payload builds correct structure."""
    payload = EventPayloadMapper.story_created_payload(
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        created_by=UserName("po-user"),
    )

    assert payload["event_type"] == "story.created"
    assert payload["story_id"] == "story-123"
    assert payload["title"] == "Test Story"
    assert payload["created_by"] == "po-user"
    assert "timestamp" in payload
    assert payload["timestamp"].endswith("Z")


def test_story_transitioned_payload():
    """Test story_transitioned_payload builds correct structure."""
    payload = EventPayloadMapper.story_transitioned_payload(
        story_id=StoryId("story-123"),
        from_state=StoryState(StoryStateEnum.DRAFT),
        to_state=StoryState(StoryStateEnum.PO_REVIEW),
        transitioned_by=UserName("po-user"),
    )

    assert payload["event_type"] == "story.transitioned"
    assert payload["story_id"] == "story-123"
    assert payload["from_state"] == "DRAFT"
    assert payload["to_state"] == "PO_REVIEW"
    assert payload["transitioned_by"] == "po-user"
    assert "timestamp" in payload


def test_decision_approved_payload_with_comment():
    """Test decision_approved_payload with comment."""
    payload = EventPayloadMapper.decision_approved_payload(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        approved_by=UserName("po-user"),
        comment=Comment("Looks good"),
    )

    assert payload["event_type"] == "decision.approved"
    assert payload["story_id"] == "story-123"
    assert payload["decision_id"] == "decision-456"
    assert payload["approved_by"] == "po-user"
    assert payload["comment"] == "Looks good"
    assert "timestamp" in payload


def test_decision_approved_payload_without_comment():
    """Test decision_approved_payload without comment."""
    payload = EventPayloadMapper.decision_approved_payload(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        approved_by=UserName("po-user"),
        comment=None,
    )

    assert payload["comment"] is None


def test_decision_rejected_payload():
    """Test decision_rejected_payload builds correct structure."""
    payload = EventPayloadMapper.decision_rejected_payload(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        rejected_by=UserName("po-user"),
        reason=Reason("Needs revision"),
    )

    assert payload["event_type"] == "decision.rejected"
    assert payload["story_id"] == "story-123"
    assert payload["decision_id"] == "decision-456"
    assert payload["rejected_by"] == "po-user"
    assert payload["reason"] == "Needs revision"
    assert "timestamp" in payload


def test_timestamp_format():
    """Test that timestamps are in ISO format with Z suffix."""
    payload = EventPayloadMapper.story_created_payload(
        story_id=StoryId("test"),
        title=Title("Test"),
        created_by=UserName("user"),
    )

    timestamp = payload["timestamp"]
    assert timestamp.endswith("Z")
    # Should be parseable as ISO datetime
    parsed = datetime.fromisoformat(timestamp.rstrip("Z"))
    assert parsed is not None
