"""Unit tests for NATSMessagingAdapter."""

import json
from unittest.mock import AsyncMock

import pytest

from planning.infrastructure.adapters import NATSMessagingAdapter


@pytest.fixture
def nats_client():
    """Create mock NATS client."""
    return AsyncMock()


@pytest.fixture
def jetstream():
    """Create mock JetStream."""
    return AsyncMock()


@pytest.fixture
def messaging_adapter(nats_client, jetstream):
    """Create messaging adapter with mocked NATS."""
    return NATSMessagingAdapter(
        nats_client=nats_client,
        jetstream=jetstream,
    )


@pytest.mark.asyncio
async def test_publish_story_created(messaging_adapter, jetstream):
    """Test publish_story_created publishes to NATS JetStream."""
    await messaging_adapter.publish_story_created(
        story_id="story-123",
        title="Test Story",
        created_by="po-user",
    )

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify subject and payload
    call_args = jetstream.publish.call_args
    assert call_args[0][0] == "planning.story.created"

    payload = json.loads(call_args[0][1].decode("utf-8"))
    assert payload["story_id"] == "story-123"
    assert payload["title"] == "Test Story"
    assert payload["created_by"] == "po-user"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_publish_story_transitioned(messaging_adapter, jetstream):
    """Test publish_story_transitioned publishes to NATS JetStream."""
    await messaging_adapter.publish_story_transitioned(
        story_id="story-123",
        from_state="DRAFT",
        to_state="PO_REVIEW",
        transitioned_by="po-user",
    )

    jetstream.publish.assert_awaited_once()

    call_args = jetstream.publish.call_args
    assert call_args[0][0] == "planning.story.transitioned"

    payload = json.loads(call_args[0][1].decode("utf-8"))
    assert payload["story_id"] == "story-123"
    assert payload["from_state"] == "DRAFT"
    assert payload["to_state"] == "PO_REVIEW"
    assert payload["transitioned_by"] == "po-user"


@pytest.mark.asyncio
async def test_publish_decision_approved(messaging_adapter, jetstream):
    """Test publish_decision_approved publishes to NATS JetStream."""
    await messaging_adapter.publish_decision_approved(
        story_id="story-123",
        decision_id="decision-456",
        approved_by="po-user",
        comment="Looks good",
    )

    jetstream.publish.assert_awaited_once()

    call_args = jetstream.publish.call_args
    assert call_args[0][0] == "planning.decision.approved"

    payload = json.loads(call_args[0][1].decode("utf-8"))
    assert payload["story_id"] == "story-123"
    assert payload["decision_id"] == "decision-456"
    assert payload["approved_by"] == "po-user"
    assert payload["comment"] == "Looks good"


@pytest.mark.asyncio
async def test_publish_decision_approved_no_comment(messaging_adapter, jetstream):
    """Test publish_decision_approved without optional comment."""
    await messaging_adapter.publish_decision_approved(
        story_id="story-123",
        decision_id="decision-456",
        approved_by="po-user",
        comment=None,
    )

    jetstream.publish.assert_awaited_once()

    call_args = jetstream.publish.call_args
    payload = json.loads(call_args[0][1].decode("utf-8"))
    assert payload["comment"] is None


@pytest.mark.asyncio
async def test_publish_decision_rejected(messaging_adapter, jetstream):
    """Test publish_decision_rejected publishes to NATS JetStream."""
    await messaging_adapter.publish_decision_rejected(
        story_id="story-123",
        decision_id="decision-456",
        rejected_by="po-user",
        reason="Needs revision",
    )

    jetstream.publish.assert_awaited_once()

    call_args = jetstream.publish.call_args
    assert call_args[0][0] == "planning.decision.rejected"

    payload = json.loads(call_args[0][1].decode("utf-8"))
    assert payload["story_id"] == "story-123"
    assert payload["decision_id"] == "decision-456"
    assert payload["rejected_by"] == "po-user"
    assert payload["reason"] == "Needs revision"


@pytest.mark.asyncio
async def test_publish_error_handling(messaging_adapter, jetstream):
    """Test publish handles NATS errors gracefully."""
    jetstream.publish.side_effect = Exception("NATS connection error")

    # Should raise the exception (no silent failures)
    with pytest.raises(Exception, match="NATS connection error"):
        await messaging_adapter.publish_story_created(
            story_id="story-123",
            title="Test",
            created_by="user",
        )

