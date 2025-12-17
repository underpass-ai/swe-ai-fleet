"""Unit tests for NATSMessagingAdapter."""

from unittest.mock import AsyncMock

import pytest
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
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.infrastructure.adapters.nats_messaging_adapter import NATSMessagingAdapter


@pytest.fixture
def nats_client():
    """Create mock NATS client."""
    return AsyncMock()


@pytest.fixture
def jetstream():
    """Create mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def messaging_adapter(nats_client, jetstream):
    """Create messaging adapter with mocked NATS and JetStream."""
    return NATSMessagingAdapter(
        nats_client=nats_client,
        jetstream=jetstream,
    )


@pytest.mark.asyncio
async def test_publish_story_created(messaging_adapter, jetstream):
    """Test publish_story_created publishes to NATS JetStream."""
    await messaging_adapter.publish_story_created(
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        created_by=UserName("po-user"),
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == str(NATSSubject.STORY_CREATED)
    assert b"story-123" in payload_bytes
    assert b"Test Story" in payload_bytes
    assert b"po-user" in payload_bytes


@pytest.mark.asyncio
async def test_publish_story_transitioned(messaging_adapter, jetstream):
    """Test publish_story_transitioned publishes to NATS JetStream."""
    await messaging_adapter.publish_story_transitioned(
        story_id=StoryId("story-123"),
        from_state=StoryState(StoryStateEnum.DRAFT),
        to_state=StoryState(StoryStateEnum.PO_REVIEW),
        transitioned_by=UserName("po-user"),
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == str(NATSSubject.STORY_TRANSITIONED)
    assert b"story-123" in payload_bytes
    assert b"DRAFT" in payload_bytes
    assert b"PO_REVIEW" in payload_bytes
    assert b"po-user" in payload_bytes


@pytest.mark.asyncio
async def test_publish_decision_approved(messaging_adapter, jetstream):
    """Test publish_decision_approved publishes to NATS JetStream."""
    await messaging_adapter.publish_decision_approved(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        approved_by=UserName("po-user"),
        comment=Comment("Looks good"),
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == str(NATSSubject.DECISION_APPROVED)
    assert b"story-123" in payload_bytes
    assert b"decision-456" in payload_bytes
    assert b"po-user" in payload_bytes
    assert b"Looks good" in payload_bytes


@pytest.mark.asyncio
async def test_publish_decision_approved_no_comment(messaging_adapter, jetstream):
    """Test publish_decision_approved without optional comment."""
    await messaging_adapter.publish_decision_approved(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        approved_by=UserName("po-user"),
        comment=None,
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_decision_rejected(messaging_adapter, jetstream):
    """Test publish_decision_rejected publishes to NATS JetStream."""
    await messaging_adapter.publish_decision_rejected(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        rejected_by=UserName("po-user"),
        reason=Reason("Needs revision"),
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == str(NATSSubject.DECISION_REJECTED)
    assert b"story-123" in payload_bytes
    assert b"decision-456" in payload_bytes
    assert b"po-user" in payload_bytes
    assert b"Needs revision" in payload_bytes


@pytest.mark.asyncio
async def test_publish_ceremony_started(messaging_adapter, jetstream):
    """Test publish_ceremony_started publishes to NATS JetStream."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)
    started_by = UserName("po-user")
    started_at = datetime.now(UTC)

    await messaging_adapter.publish_ceremony_started(
        ceremony_id=ceremony_id,
        status=status,
        total_stories=5,
        deliberations_submitted=15,
        started_by=started_by,
        started_at=started_at,
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == str(NATSSubject.BACKLOG_REVIEW_CEREMONY_STARTED)
    assert b"ceremony-123" in payload_bytes
    assert b"IN_PROGRESS" in payload_bytes
    assert b"po-user" in payload_bytes
    assert b"5" in payload_bytes  # total_stories
    assert b"15" in payload_bytes  # deliberations_submitted


@pytest.mark.asyncio
async def test_publish_ceremony_started_error_handling(messaging_adapter, jetstream):
    """Test publish_ceremony_started handles NATS errors."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)
    started_by = UserName("po-user")
    started_at = datetime.now(UTC)

    jetstream.publish.side_effect = Exception("NATS connection error")

    # Should raise the exception (no silent failures)
    with pytest.raises(Exception, match="NATS connection error"):
        await messaging_adapter.publish_ceremony_started(
            ceremony_id=ceremony_id,
            status=status,
            total_stories=5,
            deliberations_submitted=15,
            started_by=started_by,
            started_at=started_at,
        )


@pytest.mark.asyncio
async def test_publish_ceremony_started_with_different_statuses(messaging_adapter, jetstream):
    """Test publish_ceremony_started with different ceremony statuses."""
    ceremony_id = BacklogReviewCeremonyId("ceremony-456")
    started_by = UserName("admin")
    started_at = datetime.now(UTC)

    statuses = [
        BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
    ]

    for status in statuses:
        await messaging_adapter.publish_ceremony_started(
            ceremony_id=ceremony_id,
            status=status,
            total_stories=3,
            deliberations_submitted=9,
            started_by=started_by,
            started_at=started_at,
        )

        # Verify subject is correct
        call_args = jetstream.publish.call_args
        assert call_args[0][0] == str(NATSSubject.BACKLOG_REVIEW_CEREMONY_STARTED)
        assert status.to_string().encode() in call_args[0][1]

        jetstream.publish.reset_mock()


@pytest.mark.asyncio
async def test_publish_error_handling(messaging_adapter, jetstream):
    """Test publish handles NATS errors gracefully."""
    jetstream.publish.side_effect = Exception("NATS connection error")

    # Should raise the exception (no silent failures)
    with pytest.raises(Exception, match="NATS connection error"):
        await messaging_adapter.publish_story_created(
            story_id=StoryId("story-123"),
            title=Title("Test"),
            created_by=UserName("user"),
        )
