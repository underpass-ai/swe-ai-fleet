"""Unit tests for NATSMessagingAdapter."""

import json
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
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.task_id import TaskId
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
        epic_id=EpicId("epic-456"),
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
    assert b"epic-456" in payload_bytes
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
            epic_id=EpicId("epic-123"),
            title=Title("Test"),
            created_by=UserName("user"),
        )


@pytest.mark.asyncio
async def test_publish_event_wraps_payload_in_envelope(messaging_adapter, jetstream):
    """Test publish_event wraps payload in EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    payload = {
        "story_id": "story-123",
        "title": "Test Story",
        "operation": "create_story",
    }

    await messaging_adapter.publish_event("planning.story.created", payload)

    jetstream.publish.assert_awaited_once()
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == "planning.story.created"
    decoded = json.loads(payload_bytes.decode("utf-8"))
    assert decoded["event_type"] == "planning.story.created"
    assert decoded["producer"] == "planning-service"
    assert decoded["payload"] == payload
    assert "idempotency_key" in decoded
    assert "correlation_id" in decoded


@pytest.mark.asyncio
async def test_publish_event_with_plan_id(messaging_adapter, jetstream):
    """Test publish_event() uses plan_id in payload for envelope entity."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    payload = {
        "plan_id": "plan-123",
        "story_id": "story-456",
        "approved_by": "po-user",
    }

    await messaging_adapter.publish_event("planning.plan.approved", payload)

    # Verify JetStream publish was called
    jetstream.publish.assert_awaited_once()

    # Verify envelope was created and published
    call_args = jetstream.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert subject == "planning.plan.approved"
    decoded = json.loads(payload_bytes.decode("utf-8"))

    # Verify envelope structure
    assert decoded["event_type"] == "planning.plan.approved"
    assert decoded["idempotency_key"] is not None
    assert decoded["correlation_id"] is not None
    assert decoded["producer"] == "planning-service"
    assert decoded["payload"] == payload
    assert decoded["payload"]["plan_id"] == "plan-123"


@pytest.mark.asyncio
async def test_publish_event_with_ceremony_id(messaging_adapter, jetstream):
    """Test publish_event() uses ceremony_id in payload for envelope entity."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    payload = {
        "ceremony_id": "ceremony-789",
        "status": "completed",
    }

    await messaging_adapter.publish_event("planning.backlog_review.ceremony.completed", payload)

    # Verify envelope was created with ceremony_id as entity_id
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["payload"]["ceremony_id"] == "ceremony-789"


@pytest.mark.asyncio
async def test_publish_event_with_story_id_fallback(messaging_adapter, jetstream):
    """Test publish_event() falls back to story_id if plan_id/ceremony_id not present."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    payload = {
        "story_id": "story-999",
        "data": "test",
    }

    await messaging_adapter.publish_event("planning.story.updated", payload)

    # Verify envelope was created with story_id as entity_id
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["payload"]["story_id"] == "story-999"


@pytest.mark.asyncio
async def test_publish_event_with_unknown_entity_id(messaging_adapter, jetstream):
    """Test publish_event() uses 'unknown' if no entity_id found."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    payload = {
        "data": "test",
        "no_id_field": "value",
    }

    await messaging_adapter.publish_event("planning.unknown.event", payload)

    # Verify envelope was created with 'unknown' as entity_id
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.unknown.event"
    assert decoded["payload"] == payload


@pytest.mark.asyncio
async def test_publish_story_created_uses_envelope(messaging_adapter, jetstream):
    """Test that publish_story_created now uses EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    await messaging_adapter.publish_story_created(
        story_id=StoryId("story-123"),
        epic_id=EpicId("epic-456"),
        title=Title("Test Story"),
        created_by=UserName("po-user"),
    )

    # Verify envelope structure in published message
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.story.created"
    assert decoded["idempotency_key"] is not None
    assert decoded["correlation_id"] is not None
    assert decoded["producer"] == "planning-service"
    assert decoded["payload"]["story_id"] == "story-123"
    assert decoded["payload"]["epic_id"] == "epic-456"


@pytest.mark.asyncio
async def test_publish_story_transitioned_uses_envelope(messaging_adapter, jetstream):
    """Test that publish_story_transitioned now uses EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    await messaging_adapter.publish_story_transitioned(
        story_id=StoryId("story-123"),
        from_state=StoryState(StoryStateEnum.DRAFT),
        to_state=StoryState(StoryStateEnum.PO_REVIEW),
        transitioned_by=UserName("po-user"),
    )

    # Verify envelope structure
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.story.transitioned"
    assert decoded["idempotency_key"] is not None
    assert "transition_DRAFT_to_PO_REVIEW" in decoded["idempotency_key"] or decoded["payload"]["from_state"] == "DRAFT"


@pytest.mark.asyncio
async def test_publish_decision_approved_uses_envelope(messaging_adapter, jetstream):
    """Test that publish_decision_approved now uses EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    await messaging_adapter.publish_decision_approved(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        approved_by=UserName("po-user"),
        comment=Comment("Looks good"),
    )

    # Verify envelope structure
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.decision.approved"
    assert decoded["idempotency_key"] is not None
    assert decoded["payload"]["decision_id"] == "decision-456"


@pytest.mark.asyncio
async def test_publish_decision_rejected_uses_envelope(messaging_adapter, jetstream):
    """Test that publish_decision_rejected now uses EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    await messaging_adapter.publish_decision_rejected(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        rejected_by=UserName("po-user"),
        reason=Reason("Needs revision"),
    )

    # Verify envelope structure
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.decision.rejected"
    assert decoded["idempotency_key"] is not None
    assert decoded["payload"]["decision_id"] == "decision-456"


@pytest.mark.asyncio
async def test_publish_story_tasks_not_ready_uses_envelope(messaging_adapter, jetstream):
    """Test that publish_story_tasks_not_ready now uses EventEnvelope."""
    mock_ack = AsyncMock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    jetstream.publish.return_value = mock_ack

    task_id_1 = TaskId("task-1")
    task_id_2 = TaskId("task-2")
    task_ids_without_priority = (task_id_1, task_id_2)

    await messaging_adapter.publish_story_tasks_not_ready(
        story_id=StoryId("story-123"),
        reason="Tasks missing priority",
        task_ids_without_priority=task_ids_without_priority,
        total_tasks=5,
    )

    # Verify envelope structure
    call_args = jetstream.publish.call_args
    payload_bytes = call_args[0][1]
    decoded = json.loads(payload_bytes.decode("utf-8"))

    assert decoded["event_type"] == "planning.story.tasks_not_ready"
    assert decoded["idempotency_key"] is not None
    assert decoded["correlation_id"] is not None
    assert decoded["producer"] == "planning-service"
    assert decoded["payload"]["story_id"] == "story-123"
    assert decoded["payload"]["reason"] == "Tasks missing priority"
    assert decoded["payload"]["total_tasks"] == 5
