"""Unit tests for NATSMessagingAdapter."""

from unittest.mock import AsyncMock

import pytest
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

    assert subject == "planning.story.created"
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

    assert subject == "planning.story.transitioned"
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

    assert subject == "planning.decision.approved"
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

    assert subject == "planning.decision.rejected"
    assert b"story-123" in payload_bytes
    assert b"decision-456" in payload_bytes
    assert b"po-user" in payload_bytes
    assert b"Needs revision" in payload_bytes


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
