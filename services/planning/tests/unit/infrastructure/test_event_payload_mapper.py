"""Unit tests for EventPayloadMapper."""

from datetime import UTC, datetime

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
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
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


def test_ceremony_started_payload():
    """Test ceremony_started_payload builds correct structure."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)
    started_by = UserName("po-user")
    started_at = datetime.now(UTC)

    payload = EventPayloadMapper.ceremony_started_payload(
        ceremony_id=ceremony_id,
        status=status,
        total_stories=5,
        deliberations_submitted=15,
        started_by=started_by,
        started_at=started_at,
    )

    assert payload["ceremony_id"] == "ceremony-123"
    assert payload["status"] == "IN_PROGRESS"
    assert payload["total_stories"] == 5
    assert payload["deliberations_submitted"] == 15
    assert payload["started_by"] == "po-user"
    assert payload["started_at"] == started_at.isoformat()


def test_ceremony_started_payload_with_different_status():
    """Test ceremony_started_payload with different status values."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-456")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING)
    started_by = UserName("admin")
    started_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

    payload = EventPayloadMapper.ceremony_started_payload(
        ceremony_id=ceremony_id,
        status=status,
        total_stories=3,
        deliberations_submitted=9,
        started_by=started_by,
        started_at=started_at,
    )

    assert payload["status"] == "REVIEWING"
    assert payload["started_at"] == "2024-01-15T10:30:00+00:00"


def test_ceremony_started_payload_all_fields():
    """Test ceremony_started_payload includes all required fields."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-789")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)
    started_by = UserName("test-user")
    started_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)

    payload = EventPayloadMapper.ceremony_started_payload(
        ceremony_id=ceremony_id,
        status=status,
        total_stories=10,
        deliberations_submitted=30,
        started_by=started_by,
        started_at=started_at,
    )

    # Verify all fields are present
    assert "ceremony_id" in payload
    assert "status" in payload
    assert "total_stories" in payload
    assert "deliberations_submitted" in payload
    assert "started_by" in payload
    assert "started_at" in payload

    # Verify field types
    assert isinstance(payload["ceremony_id"], str)
    assert isinstance(payload["status"], str)
    assert isinstance(payload["total_stories"], int)
    assert isinstance(payload["deliberations_submitted"], int)
    assert isinstance(payload["started_by"], str)
    assert isinstance(payload["started_at"], str)

    # Verify values
    assert payload["ceremony_id"] == "ceremony-789"
    assert payload["status"] == "IN_PROGRESS"
    assert payload["total_stories"] == 10
    assert payload["deliberations_submitted"] == 30
    assert payload["started_by"] == "test-user"
    assert payload["started_at"] == "2024-06-01T12:00:00+00:00"


def test_ceremony_started_payload_with_zero_deliberations():
    """Test ceremony_started_payload with zero deliberations submitted."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-zero")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)
    started_by = UserName("admin")
    started_at = datetime.now(UTC)

    payload = EventPayloadMapper.ceremony_started_payload(
        ceremony_id=ceremony_id,
        status=status,
        total_stories=0,
        deliberations_submitted=0,
        started_by=started_by,
        started_at=started_at,
    )

    assert payload["total_stories"] == 0
    assert payload["deliberations_submitted"] == 0
